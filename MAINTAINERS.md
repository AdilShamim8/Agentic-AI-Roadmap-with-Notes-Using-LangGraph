# Maintainers

This repository is maintained by a small editorial team. Maintainers are responsible for the technical accuracy, pedagogical quality, and stylistic consistency of the content.

## Current maintainers

- Adil Shamim - founder, lead maintainer. Owns the curriculum spine (modules 01 through 09) and the overall information architecture.
- (Maintainer openings exist for the field guide, the projects, and the eval suites. Open an issue if you want to own a section.)

## What maintainers do

- Review pull requests within one week of submission
- Approve or request changes based on the editorial bar in [CONTRIBUTING.md](CONTRIBUTING.md)
- Keep the "Last reviewed" date on every chapter current (within 90 days)
- Tag releases quarterly with a [CHANGELOG.md](CHANGELOG.md) entry
- Triage issues and flag scope conflicts for contributors before they write code
- Maintain the [ROADMAP.md](ROADMAP.md) status badges

## How maintainers are added

Maintainers are added by invitation after sustained high-quality contributions. The bar is roughly: five merged PRs that meet the `stable` editorial bar, across at least two different modules. Invitations are issued by the lead maintainer.

## Stepping down

If a maintainer becomes inactive for more than 90 days, they move to "emeritus" status. Emeritus maintainers keep their commit history attribution but lose merge permissions. They can return to active status by request.

## Editorial principles

Maintainers enforce three principles, in priority order:

1. Ship only what we have. The README and ROADMAP describe the current state of the repo, not the future state. If a chapter does not exist, it is not advertised. If a chapter is in `draft`, it is labeled as such.
2. Eval everything. An agent without an eval is a demo. A chapter without an eval is an opinion. Chapters that cannot produce an eval do not ship as `stable`.
3. Minimalism is a feature. Density over decoration. Every sentence earns its place. Every code block is runnable. Every link is checked.

These principles are not negotiable. If a PR conflicts with them, the PR changes or does not merge.
