# 05 — Postgres schema and data I/O

**What to build:** The database schema and read/write layer for both the processed data and the raw-submission catalog. Schemas are shared across all five sectors via a `sector` column (not per-sector tables). The processed layer stores normalised indicator values, precomputed Sector Index and Dimension scores, and indicator metadata (definitions, reference years, data-source attribution). The catalog tracks raw submissions (file location, submitter, timestamp, status: `pending`/`published`/`rejected`, validation report summary). Each successful pipeline run appends new timestamped rows rather than overwriting (ADR-0014). The dashboard app reads through a read-only credential; data loading uses a separate credential.

**Blocked by:** 02 — Scoring engine

**Status:** ready-for-agent

- [ ] `indicators` schema stores cleaned, normalised indicator values per district per indicator per run, with a `sector` column
- [ ] `indices` schema stores precomputed Sector Index and Dimension scores per district per run
- [ ] `metadata` schema stores indicator definitions, reference years, and data-source attribution
- [ ] Catalog table stores one row per raw submission: file location, submitter, timestamp, status, validation report summary
- [ ] Write functions accept scoring engine output and persist it as a new timestamped run (append-only)
- [ ] Read functions serve the dashboard's needs: latest-run scores by sector, per-district decomposition, national summary stats
- [ ] Round-trip verified: scoring engine output written and read back matches
