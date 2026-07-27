# Changelog

All notable changes to this repository are documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning for the curriculum structure (individual chapters evolve on their own review cycles).

## [0.2.0] - 2026-07-27

### Added

- New information architecture organized by outcome (modules 01 through 09) instead of by day
- Field guide section modeled on Alexey Grigorev's AI Engineering Field Guide
- Ten portfolio-grade project specifications in [projects/](projects/)
- Six role-specific learning paths in [learning-paths/](learning-paths/)
- Templates for chapters, projects, eval rubrics, and learning paths in [_templates/](_templates/)
- Reference implementations in [examples/](examples/)
- Interview prep and job market analysis sections
- `.github/` configuration: issue templates, PR template, CI workflow
- `.claude/` configuration: AI-assisted maintenance commands
- `STYLING.md` enforcing minimalist, density-first formatting
- `MAINTAINERS.md` documenting the editorial bar and maintainer roles
- `ROADMAP.md` with per-phase status badges

### Changed

- Renamed all folders to kebab-case with zero-padded numbers (was `Day 04 Sequential Workflows in LangGraph`, now `02-langgraph-core/02-sequential-workflows.md`)
- Rewrote README to under 4,000 characters (was 36,000); moved depth into linked documents
- Pinned all dependencies in `pyproject.toml` (was unpinned `pip install` instructions)
- Replaced unsourced statistics with sourced claims or removed them

### Removed

- The "Day 0 through Day 9" calendar structure (replaced by outcome-organized modules)
- The ASCII box-drawing roadmap diagram (replaced by a Mermaid diagram in ROADMAP.md)
- The six full-width for-the-badge shields from the README (replaced by plain text)
- References to the old repository name `Agentic-AI-Roadmap-with-Notes-Using-LangGraph`

## [0.1.0] - 2026-05-15

### Added

- Initial release with Day 0 through Day 9 of LangGraph tutorials
- README, CONTRIBUTING, LICENSE
- Ten Jupyter notebooks covering sequential, parallel, conditional, and iterative workflows
