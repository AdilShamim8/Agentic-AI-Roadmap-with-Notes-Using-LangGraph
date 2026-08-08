"""VLM (Vision-Language Model) client.

The README spec calls for image captioning via a VLM. We expose a tiny
abstraction so the rest of the codebase doesn't care which provider is
in use.

Two adapters are wired:
  - `zai` (default) — uses the bundled z-ai-web-dev-sdk Node CLI. No API
    key required in this environment.
  - `openai` — uses GPT-4o vision. Requires `OPENAI_API_KEY`.

The interface is intentionally narrow:
  - `caption_image(path: Path) -> str`
  - `chat(messages: list[dict]) -> str`  (text-only, used by the answer
    synthesizer)
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Literal

from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..utils.logging import get_logger

log = get_logger(__name__)


class VLMError(RuntimeError):
    pass


# ----------------------------------------------------------------------
# Default captioning prompt
# ----------------------------------------------------------------------
_ZAI_CAPTION_PROMPT = (
    "You are a meticulous document-image captioner. Describe the contents of "
    "this image (chart, figure, photo, diagram) in 2-4 sentences. Mention the "
    "type of image, its main visible elements, and any text visible inside it. "
    "Be concise and factual."
)

_ANSWER_SYSTEM_PROMPT = (
    "You are a multimodal document analyst. You are given a user question and "
    "a set of retrieved elements (text snippets, image captions, table rows) "
    "from one or more PDFs, each tagged with a stable citation id of the form "
    "'<doc_id>::p<page>::e<element_index>'. Your job is to write a structured "
    "answer that GROUNDS every claim in those citations."
)


class VLMClient:
    """Abstract VLM/LLM client."""

    provider: Literal["zai", "openai"]

    async def caption_image(self, image_path: Path | str, prompt: str | None = None) -> str:
        raise NotImplementedError

    async def chat(self, messages: list[dict[str, Any]], *, json_mode: bool = False) -> str:
        raise NotImplementedError


# ----------------------------------------------------------------------
# z-ai adapter (uses the bundled z-ai-web-dev-sdk via Node CLI)
# ----------------------------------------------------------------------
class ZAIVLMClient(VLMClient):
    provider = "zai"

    def __init__(self) -> None:
        # The z-ai-web-dev-sdk ships a `z-ai` Node CLI. We shell out to it.
        self._cli = os.environ.get("ZAI_CLI", "z-ai")

    async def caption_image(self, image_path: Path | str, prompt: str | None = None) -> str:
        prompt = prompt or _ZAI_CAPTION_PROMPT
        out = await self._run_vision(prompt, str(image_path))
        return out.strip()

    async def chat(self, messages: list[dict[str, Any]], *, json_mode: bool = False) -> str:
        # The z-ai CLI takes a single user prompt and optional system prompt.
        # We collapse the messages list into (system, user) pair.
        system, user = self._collapse_messages(messages)
        if json_mode:
            user = (
                user
                + "\n\nIMPORTANT: respond with a single valid JSON object and "
                "nothing else. No markdown fences, no commentary."
            )
        return await self._run_chat(user, system)

    # ---- low-level CLI wrappers -----------------------------------------------
    async def _run_chat(self, prompt: str, system: str | None) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_chat_sync, prompt, system)

    async def _run_vision(self, prompt: str, image_path: str) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_vision_sync, prompt, image_path)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def _run_chat_sync(self, prompt: str, system: str | None) -> str:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as in_f:
            in_f.write("")
            tmp = in_f.name
        out_path = tmp + ".out"
        try:
            cmd = [self._cli, "chat", "--prompt", prompt, "--output", out_path]
            if system:
                cmd += ["--system", system]
            log.debug("z-ai chat: %s", " ".join(cmd[:3]) + " ...")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120, check=False
            )
            if result.returncode != 0:
                raise VLMError(
                    f"z-ai chat failed (exit {result.returncode}): "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
            if not os.path.exists(out_path):
                # Some CLI versions print JSON to stdout.
                return self._extract_content(result.stdout)
            data = json.loads(Path(out_path).read_text())
            return self._extract_content(data)
        finally:
            for p in (tmp, out_path):
                try:
                    os.unlink(p)
                except FileNotFoundError:
                    pass

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def _run_vision_sync(self, prompt: str, image_path: str) -> str:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as in_f:
            tmp = in_f.name
        out_path = tmp + ".out"
        try:
            cmd = [
                self._cli,
                "vision",
                "--prompt",
                prompt,
                "--image",
                image_path,
                "--output",
                out_path,
            ]
            log.debug("z-ai vision: %s", " ".join(cmd[:3]) + " ...")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120, check=False
            )
            if result.returncode != 0:
                raise VLMError(
                    f"z-ai vision failed (exit {result.returncode}): "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
            if not os.path.exists(out_path):
                return self._extract_content(result.stdout)
            data = json.loads(Path(out_path).read_text())
            return self._extract_content(data)
        finally:
            for p in (tmp, out_path):
                try:
                    os.unlink(p)
                except FileNotFoundError:
                    pass

    @staticmethod
    def _extract_content(data: Any) -> str:
        """Tolerantly extract the assistant message from a chat response."""
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return data.strip()
        if isinstance(data, dict):
            if "choices" in data and data["choices"]:
                msg = data["choices"][0].get("message", {})
                if "content" in msg:
                    return str(msg["content"])
            inner = data.get("data", data)
            if isinstance(inner, dict) and "content" in inner:
                return str(inner["content"])
        return str(data).strip()

    @staticmethod
    def _collapse_messages(messages: list[dict[str, Any]]) -> tuple[str | None, str]:
        """Collapse OpenAI-style messages into (system, user) for the CLI."""
        system_parts: list[str] = []
        user_parts: list[str] = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if isinstance(content, list):
                # Multimodal content — flatten text parts.
                content = " ".join(
                    p.get("text", "") for p in content if isinstance(p, dict)
                )
            if role == "system":
                system_parts.append(content)
            else:
                user_parts.append(f"[{role}]\n{content}")
        system = "\n\n".join(system_parts) if system_parts else None
        user = "\n\n".join(user_parts)
        return system, user


# ----------------------------------------------------------------------
# OpenAI adapter (optional — used when VLM_PROVIDER=openai)
# ----------------------------------------------------------------------
class OpenAIVLMClient(VLMClient):
    provider = "openai"

    def __init__(self) -> None:
        try:
            import openai  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise VLMError(
                "openai package not installed. Run `pip install openai`."
            ) from exc
        if not settings.openai_api_key:
            raise VLMError("OPENAI_API_KEY must be set when VLM_PROVIDER=openai")
        self._api_key = settings.openai_api_key
        self._vision_model = settings.openai_vision_model
        self._chat_model = settings.openai_chat_model

    async def caption_image(self, image_path: Path | str, prompt: str | None = None) -> str:
        import openai

        prompt = prompt or _ZAI_CAPTION_PROMPT
        b64 = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")
        client = openai.AsyncOpenAI(api_key=self._api_key)
        resp = await client.chat.completions.create(
            model=self._vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ],
                }
            ],
            max_tokens=300,
        )
        return (resp.choices[0].message.content or "").strip()

    async def chat(self, messages: list[dict[str, Any]], *, json_mode: bool = False) -> str:
        import openai

        client = openai.AsyncOpenAI(api_key=self._api_key)
        kwargs: dict[str, Any] = {
            "model": self._chat_model,
            "messages": messages,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = await client.chat.completions.create(**kwargs)
        return (resp.choices[0].message.content or "").strip()


# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------
def get_vlm_client() -> VLMClient:
    """Return the VLM client configured in settings (for image captioning)."""
    if settings.vlm_provider == "zai":
        return ZAIVLMClient()
    if settings.vlm_provider == "openai":
        return OpenAIVLMClient()
    raise VLMError(f"Unknown VLM provider: {settings.vlm_provider}")


def get_llm_client() -> VLMClient:
    """Return the chat LLM client. Uses llm_provider from settings."""
    if settings.llm_provider == "zai":
        return ZAIVLMClient()
    if settings.llm_provider == "openai":
        return OpenAIVLMClient()
    raise VLMError(f"Unknown LLM provider: {settings.llm_provider}")
