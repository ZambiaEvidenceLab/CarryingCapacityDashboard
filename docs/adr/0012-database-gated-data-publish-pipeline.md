---
status: accepted (storage location amended by ADR-0016)
---

# Database-gated data publish pipeline, decoupled from app code deploys

> **Amended by [ADR-0016](0016-raw-data-lake-interim-storage.md)**: raw submissions do not live in PostgreSQL after all — they live in a data lake (interim: the private repo + local storage). The gating logic below (nothing reaches the dashboard without passing `pending` → `published`/`rejected`) still holds; only the storage location of the raw side changes.

Raw indicator submissions are tracked so that nothing reaches the dashboard unchecked, wherever they physically land — not committed to GitHub as the *published* record (supersedes [ADR-0011](0011-github-pr-data-publish-workflow.md)'s PR-as-publish-step model). Because data can arrive through paths the repository's CI never sees (a future admin tool, a script run by a data engineer, direct access during a handover/training period), nothing is trusted by default until the validation pipeline says otherwise.

**Design:**

- Raw submissions land in a `pending` state, with audit metadata (submitter, timestamp, source reference) — this is where the audit-trail need (originally scoped as committing raw files to git) now lives instead.
- The dashboard app only ever reads a `published` layer — precomputed Sector Index / Decomposition View scores ([ADR-0010](0010-precompute-static-dashboard.md)) and the indicator data behind them. It never reads `pending` rows. A DB write alone therefore cannot change what's on screen.
- A validation pipeline — code in this repository, per [ADR-0006](0006-district-master-list-from-grid3.md)/[0008](0008-winsorize-before-minmax.md) — is the only thing that promotes `pending` rows to `published`. It re-runs district-name matching against the GRID3 master list, per-indicator range/type checks, the winsorization/distribution report, and the unit test suite. Only a fully passing run promotes the data, recomputes scores, and triggers redeployment. A failing run marks the rows `rejected` with a logged reason; the last `published` data (and the live dashboard) is untouched.
- For v1, this pipeline is triggered manually — a GitHub Actions `workflow_dispatch` run by whoever loaded the new data — rather than a database webhook or polling job. This avoids building push infrastructure (Postgres `LISTEN`/`NOTIFY`, a webhook receiver) for a process that isn't yet frequent, while still guaranteeing checks run before anything goes live.

**This is deliberately a second, independent trigger from the app's own code deploy** (merging a PR to `main` auto-deploys the app per the code-review workflow already in place). A code-only change shouldn't force revalidating all data, and a validated data promotion shouldn't require a pull request.

**Open dependency — flagged for the MoFNP workshop**: this assumes the validation job can reach the database over the network. If the eventual hosting environment puts Postgres on a private network (e.g. a VPC-only Cloud SQL instance), the validation/promotion job needs to run inside that same cloud environment (e.g. a manually-triggered Cloud Run job) rather than as a GitHub Actions runner reaching out to it — a consequence of whichever hosting route the workshop picks.
