---
status: accepted
---

# Raw data lives outside PostgreSQL, in a data lake; interim storage is the private GitHub repo and local machine

Raw ministry submissions are never stored in PostgreSQL. They live in a data lake, conceptually separate from the processed database: for now (development/prototyping phase), that means files kept on the developer's laptop and committed to this **private** GitHub repository. Long-term, a proper data lake — cloud object storage (e.g. AWS S3) or physical/on-prem file storage — will replace this, chosen once hosting is settled with MoFNP (see the workshop's hosting question). PostgreSQL holds only the processed/queryable layer — the `indicators`, `indices`, and `metadata` schemas — plus a lightweight catalog of raw submissions (file location, submitter, timestamp, status: `pending`/`published`/`rejected`). There is no `raw` schema in Postgres.

This supersedes [ADR-0012](0012-database-gated-data-publish-pipeline.md)'s framing of raw data being "written directly to a secure PostgreSQL instance," and supersedes [ADR-0013](0013-immutable-parquet-raw-layer.md)'s specific mechanism (Parquet files in cloud object storage) — but keeps both ADRs' actual goal intact: raw data is immutable once received, physically separate from the processed layer, and nothing reaches the dashboard without passing through the validation pipeline's `pending` → `published`/`rejected` gate. Only *where* raw physically sits has changed.

Committing raw files to GitHub reverses an earlier instinct (raw should never be committed to git) — justified here specifically because the repository is private and this is an explicit, temporary measure for development, not the permanent design.

**Risk to flag**: git is not built for storing many raw data files over time — no lifecycle management, no partition/query layer, and its append-only history can technically be rewritten by anyone with force-push rights. Treat this as good enough for prototyping only. Branch protection (disabling force-push on `main`) is worth turning on now if git history is going to be relied on as part of the interim audit trail.

**Consequence**: don't over-build for data-lake scale prematurely. A well-organized raw file layout (e.g. `data/raw/<sector>/<date>-<submitter>.csv`) plus a manifest of submissions is enough for now. Whether a genuine data-lake platform (AWS S3 + a catalog/query layer) is worth the investment later should be decided once it's clear whether raw sources stay at "one small CSV per cycle" scale or start including larger, more heterogeneous data (e.g. raw survey microdata).
