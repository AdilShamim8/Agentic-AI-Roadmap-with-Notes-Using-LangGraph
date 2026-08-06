"""Deterministic mock LLM provider.

Used in tests, dry-runs, and when no API key is configured. The mock
implements a tiny pattern-matching heuristic so the agent can actually
complete the reproduce → diagnose → patch → verify loop on the bundled
fixtures without any network calls.

It is NOT a general code agent — it only knows how to reason about the
specific kinds of bugs in `fixtures/`. For real work, configure OpenAI
or Anthropic.
"""

from __future__ import annotations

import re

from self_heal.llm.base import LLMResponse, Message, TokenUsage

# Rough token estimate: 4 chars ≈ 1 token.
_CHARS_PER_TOKEN = 4


class MockProvider:
    """Pattern-matching mock provider."""

    name = "mock"
    model = "mock"

    def complete(self, messages: list[Message]) -> LLMResponse:
        sys_msg = next((m for m in messages if m.role == "system"), None)
        user_msgs = [m for m in messages if m.role == "user"]
        user_text = "\n".join(m.content for m in user_msgs)

        content = self._respond(sys_msg.content if sys_msg else "", user_text)

        in_tok = max(1, sum(len(m.content) for m in messages) // _CHARS_PER_TOKEN)
        out_tok = max(1, len(content) // _CHARS_PER_TOKEN)
        return LLMResponse(
            content=content,
            usage=TokenUsage(input_tokens=in_tok, output_tokens=out_tok),
            model=self.model,
        )

    # ── heuristic dispatch ─────────────────────────────────────
    def _respond(self, system: str, user: str) -> str:
        sys_l = system.lower()
        text = user.lower()

        # Order matters: the patch system prompt mentions "diagnosis" (it
        # receives the diagnosis as input), so we must check for patch-specific
        # markers BEFORE the diagnose check.
        if "unified diff" in sys_l or "writing a patch" in sys_l or "write a patch" in text:
            return self._patch(user)

        if "debugging engineer" in sys_l or "diagnos" in sys_l or "diagnos" in text:
            return self._diagnose(user)

        if "critical reviewer" in sys_l or "reflexion" in sys_l or "critique" in sys_l:
            return (
                "REFLEXION: The previous patch likely addressed the wrong line or "
                "introduced a new edge case. Re-examine the traceback's last frame "
                "and the exact operator that failed; prefer the smallest possible "
                "change that flips the failing assertion."
            )

        # Generic default.
        return "MOCK: no specific heuristic matched this prompt."

    # ── diagnose heuristic ─────────────────────────────────────
    @staticmethod
    def _diagnose(user: str) -> str:
        tb = user
        diagnosis_lines = ["## Diagnosis (mock)"]

        if "assert" in tb.lower():
            diagnosis_lines.append(
                "- Root cause: an assertion is failing because the code under test "
                "produces a value that does not match the expected value."
            )

        # Off-by-one hint.
        if re.search(r"\b(range|for|i\s*<|\[\s*i\s*\])", tb):
            diagnosis_lines.append(
                "- Likely an off-by-one in a loop bound or slice index. Check "
                "whether `<` should be `<=` (or vice versa) and whether a slice "
                "endpoint is exclusive when it should be inclusive."
            )

        # Wrong exception type.
        if "exception" in tb.lower() and "wrong type" in tb.lower():
            diagnosis_lines.append(
                "- The code raises the wrong exception type. The test expects a "
                "specific exception; the code raises a different one."
            )
        elif "exception" in tb.lower():
            diagnosis_lines.append(
                "- The code raises an exception the test does not expect, or vice "
                "versa. Inspect the `raises(...)` context manager in the test."
            )

        # Multi-file hint.
        if "import" in tb.lower() and "from" in tb.lower():
            diagnosis_lines.append(
                "- The bug may span multiple modules — the caller passes a value "
                "the callee mishandles. Patch both sides if needed."
            )

        diagnosis_lines.append(
            "- Suggested fix: make the smallest change that flips the failing "
            "assertion without altering other behavior."
        )
        return "\n".join(diagnosis_lines)

    # ── patch heuristic ────────────────────────────────────────
    @staticmethod
    def _patch(user: str) -> str:
        """Emit a targeted unified diff by parsing the source from the prompt.

        The mock extracts the file path + content from the `# File: ...` blocks
        in the prompt, looks for one of a few known bug patterns, and emits a
        diff with correct context lines so it actually applies. This is enough
        to make the bundled fixtures pass end-to-end without an API key.
        """
        # Find all `# File: <path>` + ```python ... ``` blocks in the prompt.
        file_blocks: list[tuple[str, list[str]]] = []
        for m in re.finditer(r"# File:\s*(\S+)\s*```python\n(.*?)```", user, re.DOTALL):
            path = m.group(1).strip()
            content = m.group(2).splitlines()
            file_blocks.append((path, content))

        if not file_blocks:
            # Fallback: no source found.
            return "```diff\n(no source files found in prompt — mock cannot patch)\n```"

        # Pick which bug patterns to try based on context keywords in the prompt
        # (diagnosis + source). This prevents e.g. the wrong-exception pattern
        # firing on `raise ValueError("empty list")` in the percentile fixture.
        text_l = user.lower()
        patterns = []
        if any(k in text_l for k in ("sum_range", "off-by-one", "off by one", "range(start")):
            patterns.append(
                (
                    re.compile(r"for\s+i\s+in\s+range\((\w+),\s*(\w+)\):"),
                    lambda m: (
                        m.group(0),
                        m.group(0).replace(
                            f"range({m.group(1)}, {m.group(2)})",
                            f"range({m.group(1)}, {m.group(2)} + 1)",
                        ),
                    ),
                )
            )
        if any(k in text_l for k in ("divide", "denominator", "zerodivision")):
            patterns.append(
                (
                    re.compile(r"raise\s+ValueError\("),
                    lambda m: (m.group(0), m.group(0).replace("ValueError", "ZeroDivisionError")),
                )
            )
        if any(k in text_l for k in ("percentile", "select(", "rank")):
            patterns.append(
                (
                    re.compile(r"return\s+select\((\w+),\s*(\w+)\)"),
                    lambda m: (
                        m.group(0),
                        m.group(0).replace(
                            f"select({m.group(1)}, {m.group(2)})",
                            f"select({m.group(1)}, {m.group(2)} - 1)",
                        ),
                    ),
                )
            )
        # Fallback: if no keywords matched, try all patterns (best-effort).
        if not patterns:
            patterns = [
                (
                    re.compile(r"for\s+i\s+in\s+range\((\w+),\s*(\w+)\):"),
                    lambda m: (
                        m.group(0),
                        m.group(0).replace(
                            f"range({m.group(1)}, {m.group(2)})",
                            f"range({m.group(1)}, {m.group(2)} + 1)",
                        ),
                    ),
                ),
                (
                    re.compile(r"raise\s+ValueError\("),
                    lambda m: (m.group(0), m.group(0).replace("ValueError", "ZeroDivisionError")),
                ),
                (
                    re.compile(r"return\s+select\((\w+),\s*(\w+)\)"),
                    lambda m: (
                        m.group(0),
                        m.group(0).replace(
                            f"select({m.group(1)}, {m.group(2)})",
                            f"select({m.group(1)}, {m.group(2)} - 1)",
                        ),
                    ),
                ),
            ]

        for path, lines in file_blocks:
            for idx, line in enumerate(lines):
                for pat, transform in patterns:
                    m = pat.search(line)
                    if m:
                        old_snippet, new_snippet = transform(m)
                        # Use the FULL original line (preserving indentation and
                        # trailing comments) as the removed line, and replace
                        # only the matched snippet within it for the added line.
                        old_line = line.rstrip("\n")
                        new_line = old_line.replace(old_snippet, new_snippet, 1)

                        # Build a minimal unified diff with 1 line of context above and below.
                        old_start = idx  # 0-indexed; will become 1-indexed in header
                        context_before = lines[idx - 1].rstrip("\n") if idx > 0 else None
                        context_after = (
                            lines[idx + 1].rstrip("\n") if idx + 1 < len(lines) else None
                        )

                        diff_lines = [f"--- a/{path}", f"+++ b/{path}"]
                        hunk_body = []
                        hunk_old_count = 0
                        hunk_new_count = 0
                        if context_before is not None:
                            hunk_body.append(f" {context_before}")
                            hunk_old_count += 1
                            hunk_new_count += 1
                            old_start = idx - 1
                        hunk_body.append(f"-{old_line}")
                        hunk_old_count += 1
                        hunk_body.append(f"+{new_line}")
                        hunk_new_count += 1
                        if context_after is not None:
                            hunk_body.append(f" {context_after}")
                            hunk_old_count += 1
                            hunk_new_count += 1
                        diff_lines.append(
                            f"@@ -{old_start + 1},{hunk_old_count} +{old_start + 1},{hunk_new_count} @@"
                        )
                        diff_lines.extend(hunk_body)
                        return "```diff\n" + "\n".join(diff_lines) + "\n```"

        # No known pattern matched — emit a no-op diff so the agent doesn't crash.
        path = file_blocks[0][0]
        return f"```diff\n--- a/{path}\n+++ b/{path}\n@@ -1,1 +1,1 @@\n # (mock could not identify a known bug pattern)\n```"
