---
status: superseded by ADR-0016
---

# Raw indicator data stored as immutable Parquet files; Postgres holds the catalog and processed layer

> **Superseded**: the Parquet-in-cloud-object-storage mechanism described here was deferred — see [ADR-0016](0016-raw-data-lake-interim-storage.md) for the interim (private repo + local) storage actually in use, and the long-term data lake choice (still open). Kept for the record of the goal (immutable-by-construction raw storage, Postgres never holding raw) — ADR-0016 keeps that goal but hasn't yet locked in this specific mechanism.

Every raw submission is written once as a compressed Parquet file in object storage, keyed so it is never overwritten or edited in place — raw data is immutable by construction, not just by convention. Postgres holds two things instead of the raw values themselves: a lightweight catalog table (submission → storage path, submitter, timestamp, status of `pending`/`published`/`rejected` per [ADR-0012](0012-database-gated-data-publish-pipeline.md)), and the processed/published layer — cleaned indicator values and precomputed Sector Index / Decomposition View scores ([ADR-0010](0010-precompute-static-dashboard.md)) — which is what the dashboard app actually queries.

This is the standard raw/processed ("bronze/silver") separation in data engineering, and it turns "never overwrite raw data" from a rule someone has to remember into a structural guarantee: a new submission is always a new file, so there's no write path that could accidentally destroy history. Parquet's columnar compression keeps this cheap even as years of submissions accumulate, and object storage is a better fit than Postgres rows for something written once and rarely queried directly — Postgres's job is serving the queries the dashboard needs, not being a file store.

A **rejected** submission's raw file is kept untouched, exactly like a published one. Rejection only means the processed/published layer is never derived from it — the evidence of what was actually submitted is never deleted.

**Consequence**: introduces an object storage dependency alongside Postgres — tied to whichever hosting route the MoFNP workshop picks (e.g. a GCS bucket if GCP, an equivalent elsewhere).
