# Contributing

Contributions are welcome. This document describes the editorial bar, the templates, the review process, and the conventions that every file in this repository follows.

Read [STYLING.md](STYLING.md) before opening a pull request. PRs that violate the styling rules will be requested for changes.

## What we are looking for

The highest-value contributions are:

- New chapters in modules 04 through 09 (currently in `draft` or `beta` status)
- Reference implementations for the projects in [projects/](projects/)
- Golden datasets and evaluators for existing chapters
- Corrections to technical inaccuracies, especially around rapidly-evolving APIs (LangGraph, MCP, A2A)
- Translations of the learning paths into other languages

The lowest-value contributions are:

- Cosmetic changes that do not improve signal density
- New chapters in modules 01 through 03 (these are stable; changes need a strong reason)
- Content that duplicates what already exists elsewhere in the repo

## Before you write

Open an issue first. Describe what you want to add or change, and why. A maintainer will respond within a week to confirm scope, suggest a location, and flag any conflicts with in-progress work. This avoids the situation where you spend two days on a PR that gets rejected because the work is already in flight.

## Use the templates

Every new chapter, project, eval rubric, and learning path uses a template from [_templates/](_templates/). The templates are the contract that enforces consistency. Do not invent your own structure.

- [Chapter template](_templates/chapter.md) - for any new topic chapter
- [Project template](_templates/project.md) - for any new portfolio project
- [Eval rubric template](_templates/eval-rubric.md) - for any new evaluation suite
- [Learning path template](_templates/learning-path.md) - for any new role-specific path

## Editorial bar

Every chapter that ships as `stable` must meet the bar below. Chapters in `draft` or `beta` are explicitly marked as such and do not need to meet the full bar — but they should be making progress toward it.

A `stable` chapter:

- Follows the [chapter template](_templates/chapter.md) exactly
- Has runnable code in a paired `.py` + `.ipynb` format (the `.py` is the source of truth; the notebook imports and demonstrates)
- Has at least one `test_*.py` file that runs in CI
- Has at least a 10-row golden dataset in CSV
- Has at least one evaluator (rule-based or LLM-as-judge)
- Has been reviewed for technical accuracy against the latest version of the relevant API
- Has a "Last reviewed" date within 90 days
- Follows every rule in [STYLING.md](STYLING.md)

## Pull request process

1. Fork the repository and create a branch from `main`
2. If you are adding new content, open an issue first (see "Before you write")
3. Write the content using the appropriate template
4. Run `make lint` and `make test` locally; both must pass
5. If your change affects an agent, run `make eval` and include the eval diff in the PR description
6. Open the PR with a clear title and a description that explains what changed and why
7. Link the issue your PR addresses

A maintainer will review within a week. Review focuses on: technical accuracy, adherence to the templates and styling rules, signal density (no padding), and whether the content earns its place in the repo.

## Git commit messages

Use the present tense and imperative mood:

- "Add MCP server chapter" not "Added MCP server chapter"
- "Fix typo in eval section" not "Fixes typo in eval section"

Limit the first line to 72 characters. Reference the issue number in the body if applicable.

Optional prefixes:

- `docs:` for documentation-only changes
- `code:` for changes to code examples
- `eval:` for changes to eval suites or datasets
- `fix:` for bug fixes
- `chore:` for maintenance (dependency bumps, CI config)

## Code style

Python code follows PEP 8 with a 100-character line length. Type hints are required on all function signatures. Docstrings are required on all public functions.

Code examples in chapters should be small enough to read in one sitting but realistic enough that the failure modes are visible. Avoid toy domains (BMI calculators, quadratic equation solvers) when a real domain works at the same size — a 30-line invoice-extraction agent teaches more than a 30-line BMI agent because the failure modes (PII, schema drift, missing fields) are real.

Every code example must include:

- Error handling for LLM API failures (timeouts, rate limits, 5xx)
- Structured logging (not `print`)
- Type hints
- A docstring on the public surface

## Review process

The review process has three stages:

1. Technical accuracy - does the code run? Does it use the current API? Are the claims correct?
2. Pedagogical clarity - does the chapter teach the concept? Does the worked example expose the right failure modes? Does the eval measure the right thing?
3. Stylistic consistency - does it follow STYLING.md? Does it match the voice of the surrounding chapters?

A PR must pass all three stages to merge. Reviewers will request changes for any stage that does not pass.

## Community

Discussion happens in GitHub Issues and PRs. Be respectful, be concrete, be direct. Disagreements about technical direction are welcome; personal attacks are not. The [Code of Conduct](CODE_OF_CONDUCT.md) applies to all participation.

## Attribution

This Contributing Guide is adapted from the Atom Contributing Guide and the AI Engineering Field Guide by Alexey Grigorev.
