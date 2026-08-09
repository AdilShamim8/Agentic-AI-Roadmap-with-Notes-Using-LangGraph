"""Human-in-the-loop approval gate.

Provides :class:`HITLManager` with two backends:

* **CLI** (default) — pretty-prints the proposed action with ``rich`` and
  prompts the operator for ``y`` / ``n`` / ``m`` (modify). Runs in a thread
  via :func:`asyncio.to_thread` so the event loop is never blocked.

* **Slack** — posts a Block Kit message with Approve / Deny buttons to the
  configured Slack incoming webhook, then waits for an interactive callback.
  **Limitation:** receiving Slack interactive callbacks requires a publicly
  reachable HTTPS endpoint, which is not trivially simulatable in local / dev
  environments. Consequently the Slack backend starts a short poll loop and
  defaults to **denied** after ``_SLACK_TIMEOUT_SEC`` (30 s) if no approval
  arrives. If ``slack_webhook_url`` is empty the backend transparently falls
  back to CLI.

``rich`` and ``httpx`` are lazy-imported so this module loads without them.
"""

from __future__ import annotations

import asyncio
from typing import Optional, Tuple

import structlog

from anomaly_monitor.config import HitlBackend, Settings, settings as _default_settings
from anomaly_monitor.models import Action

log = structlog.get_logger()

_SLACK_TIMEOUT_SEC = 30  # could be promoted to Settings if tunability is needed


class HITLManager:
    """Human-in-the-loop approval manager (CLI or Slack backend)."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """Initialise the manager.

        Args:
            settings: Project settings (defaults to the global singleton).
                The ``hitl_backend`` field selects CLI vs Slack.
        """
        self._settings = settings or _default_settings
        self._backend = self._settings.hitl_backend

    async def request_approval(
        self, action: Action
    ) -> Tuple[bool, Optional[Action]]:
        """Ask a human to approve (or modify) the proposed action.

        Args:
            action: The proposed :class:`Action` to review.

        Returns:
            ``(approved, modified_action)``. If approved without modification,
            ``modified_action`` is ``None``. If the operator modifies the
            action, ``modified_action`` is the new :class:`Action`. On denial
            or timeout, returns ``(False, None)``.
        """
        if self._backend == HitlBackend.SLACK:
            if self._settings.slack_webhook_url:
                return await self._slack_review(action)
            log.info("hitl_slack_no_webhook_fallback_cli")
        return await self._cli_review(action)

    # ------------------------------------------------------------------
    # CLI backend
    # ------------------------------------------------------------------
    async def _cli_review(
        self, action: Action
    ) -> Tuple[bool, Optional[Action]]:
        """Run the blocking rich prompt in a worker thread."""
        try:
            return await asyncio.to_thread(self._cli_prompt, action)
        except Exception as exc:  # noqa: BLE001
            log.warning("hitl_cli_error_defaulting_deny", error=str(exc))
            return False, None

    def _cli_prompt(self, action: Action) -> Tuple[bool, Optional[Action]]:
        """Synchronous rich-based prompt (run inside a thread)."""
        from rich.console import Console  # lazy
        from rich.panel import Panel
        from rich.prompt import Prompt
        from rich.table import Table

        console = Console()
        table = Table(title="Proposed Action", show_header=False, expand=True)
        table.add_column("Field", style="cyan", no_wrap=True)
        table.add_column("Value")
        table.add_row("Kind", str(action.kind))
        table.add_row("Severity", action.severity.value)
        table.add_row("Target", action.target)
        table.add_row("Payload", str(action.payload))
        table.add_row("Dry-run", str(action.dry_run))
        console.print(Panel(table, border_style="yellow", title="HITL Review"))

        resp = Prompt.ask(
            "Approve? [y/n/m <new_kind>]",
            default="n",
            console=console,
        ).strip()
        if not resp:
            return False, None
        resp = resp.lower()

        if resp in ("y", "yes"):
            return True, None

        if resp.startswith("m"):
            parts = resp.split(maxsplit=1)
            if len(parts) > 1 and parts[1] in ("noop", "alert", "scale", "block"):
                new_kind = parts[1]
            else:
                new_kind = Prompt.ask(
                    "New action kind",
                    choices=["noop", "alert", "scale", "block"],
                    default="noop",
                    console=console,
                )
            new_target = Prompt.ask(
                "New target", default=action.target, console=console
            )
            modified = action.model_copy(
                update={"kind": new_kind, "target": new_target}  # type: ignore[arg-type]
            )
            log.info("hitl_modified", new_kind=new_kind, new_target=new_target)
            return True, modified

        return False, None

    # ------------------------------------------------------------------
    # Slack backend
    # ------------------------------------------------------------------
    async def _slack_review(
        self, action: Action
    ) -> Tuple[bool, Optional[Action]]:
        """Post a Block Kit message to Slack and wait for approval.

        .. note::
            **Limitation:** receiving Slack interactive callbacks requires a
            publicly reachable request URL. In environments without one
            (local dev, CI) this method posts the message, waits
            ``_SLACK_TIMEOUT_SEC`` seconds, then defaults to **denied**.
            In production, wire the Slack interactive endpoint to call back
            into an approval store that this poll loop checks.
        """
        import httpx  # lazy

        webhook = self._settings.slack_webhook_url
        if not webhook:
            log.info("hitl_slack_no_webhook_fallback_cli")
            return await self._cli_review(action)

        blocks = self._build_slack_blocks(action)
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    webhook,
                    json={"text": f"Action approval: {action.kind}", "blocks": blocks},
                    timeout=10.0,
                )
                if r.status_code >= 300:
                    log.warning(
                        "hitl_slack_post_failed_fallback_cli",
                        status=r.status_code,
                        body=r.text[:200],
                    )
                    return await self._cli_review(action)
        except Exception as exc:  # noqa: BLE001
            log.warning("hitl_slack_error_fallback_cli", error=str(exc))
            return await self._cli_review(action)

        log.info("hitl_slack_posted_waiting", timeout_sec=_SLACK_TIMEOUT_SEC)
        # Without a public interactive endpoint we cannot receive the button
        # callback. Default to DENY after the timeout.
        await asyncio.sleep(_SLACK_TIMEOUT_SEC)
        log.warning("hitl_slack_timeout_defaulting_deny")
        return False, None

    @staticmethod
    def _build_slack_blocks(action: Action) -> list[dict]:
        """Build a Slack Block Kit message body for the action."""
        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Action Approval Request"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Kind:*\n{action.kind}"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{action.severity.value}"},
                    {"type": "mrkdwn", "text": f"*Target:*\n{action.target}"},
                    {"type": "mrkdwn", "text": f"*Dry-run:*\n{action.dry_run}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Payload:*\n```{action.payload}```",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve"},
                        "style": "primary",
                        "value": "approve",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Deny"},
                        "style": "danger",
                        "value": "deny",
                    },
                ],
            },
        ]

    async def aclose(self) -> None:
        """No-op (symmetry with other async managers)."""
        pass
