"""Prompt templates for each LLM-driven node.

Kept as plain string templates (not f-strings) so the prompts are easy to
audit and diff. Variables are filled with `.format(**kwargs)`.
"""

from __future__ import annotations

# ── Diagnose ─────────────────────────────────────────────────
DIAGNOSE_SYSTEM = """\
You are a senior Python debugging engineer. You are given:
1. A failing test's traceback (and pytest output).
2. The contents of the source files referenced in the traceback.

Your job is to produce a concise, correct diagnosis of the *root cause* of the
failure — not a fix yet. Identify the exact file, the exact function/line, and
the exact mistake (off-by-one, wrong exception type, wrong operator, missing
edge case, etc.). Be specific; avoid speculation.

Format your answer as:

## Diagnosis
- Failing test: <nodeid>
- Root cause: <one-paragraph explanation>
- Suspect location: <file:line>
- Hypothesis: <what change would fix it, described in prose>
- Confidence: <low|medium|high>

Do not write code or diffs in this step."""

DIAGNOSE_USER = """\
# Failing test
Target: {test_target}

# Pytest output (stdout)
```
{pytest_stdout}
```

# Traceback (last failure)
```
{traceback}
```

# Relevant source files
{source_files}

Produce the diagnosis now."""


# ── Patch ────────────────────────────────────────────────────
PATCH_SYSTEM = """\
You are a senior Python engineer writing a patch. You are given:
1. The diagnosis of the failing test.
2. The contents of the relevant source files.
3. (If this is a retry) the previous failed patch and a reflexion critique.

Write a patch as a unified diff. The diff MUST:
- Use the `--- a/<path>` / `+++ b/<path>` header form.
- Contain one or more `@@ -old,n +new,m @@` hunk headers.
- Use ` ` (space) for context lines, `-` for removed, `+` for added.
- Apply cleanly against the file contents shown below.

You MAY touch multiple files if the bug spans modules — emit a separate
`---`/`+++` block per file. Keep the patch as small as possible while still
correct. Do not refactor unrelated code.

Output ONLY the unified diff, optionally wrapped in a single ```diff fence.
No commentary outside the fence."""

PATCH_USER = """\
# Diagnosis
{diagnosis}

# Source files (current contents)
{source_files}

# Reflexion notes (if any)
{reflexion}

# Previous failed patch (if any)
{previous_patch}

Write the unified diff now."""


# ── Reflexion ────────────────────────────────────────────────
REFLEXION_SYSTEM = """\
You are a critical reviewer. A previous patch attempt failed. Examine:
1. The diagnosis that motivated the patch.
2. The patch that was applied.
3. The new pytest output / traceback after applying the patch.

Produce a short, blunt critique: what did the patch get wrong? What did it
miss? What should the next patch attempt do differently? Be specific and
actionable. Do not write code.

Format:

## Reflexion
- What went wrong: <one paragraph>
- What to try next: <one paragraph>
- Pitfalls to avoid: <bullet list>"""

REFLEXION_USER = """\
# Iteration
{iteration}

# Diagnosis that was used
{diagnosis}

# Patch that was applied
```
{patch}
```

# Verify output after applying the patch
- target_passed: {target_passed}
- failed: {failed}
- errors: {errors}

# New traceback (if any)
```
{traceback}
```

Produce the reflexion now."""
