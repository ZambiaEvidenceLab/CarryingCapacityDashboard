---
status: superseded by ADR-0012
---

# Data updates flow through GitHub pull requests, gated by CI

> **Superseded**: this ADR assumed a data update was a committed CSV file in a pull request. We decided instead that raw submissions live in Postgres, not git — see [ADR-0012](0012-database-gated-data-publish-pipeline.md). Kept for the record of why PR-based gating was the first design and what it was trying to achieve (a reviewable, auditable, checked path to publish) — ADR-0012 keeps that goal but relocates the mechanism.

A data update is a pull request against this repository (adding or replacing the relevant Excel/CSV under source control). Opening the PR triggers a GitHub Actions workflow that runs the validation script — district-name matching against the [GRID3 master list](0006-district-master-list-from-grid3.md), range/type checks, the winsorization/distribution report from [ADR-0008](0008-winsorize-before-minmax.md) — and the unit test suite for the cleaning/scoring code. A human reviewer (the ministry-designated data verifier, or the ZEL data lead in the interim) reviews and merges the PR; merging is the publish step, which recomputes Sector Index scores per [ADR-0010](0010-precompute-static-dashboard.md) and redeploys the static app.

This reuses GitHub's existing review, CI, and audit machinery (PR review, required status checks, commit history) instead of building a bespoke staging-database and admin-approval UI, and it gives the workshop's data-verification question (who signs off, and how is that recorded) a concrete answer at essentially no extra engineering cost beyond writing the checks themselves — every accepted update has a named approver and a visible diff.

**Open dependency — flagged for the MoFNP workshop**: this design assumes whoever verifies data updates is willing and able to operate through GitHub (or is handed a thin front-door onto it). It's the reason the workshop's hosting question now includes whether the handover should be the whole repository (data pipeline included) or the dashboard alone — see the README's workshop section.
