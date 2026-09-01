# 06 — Validation and publish pipeline

**What to build:** The end-to-end data intake path. A raw Excel/CSV file enters the system as a `pending` Raw Submission: the file is stored in the data lake (interim: `data/raw/<sector>/<date>-<submitter>.csv` in the repo) and a catalog entry is created in Postgres. The validation pipeline then checks the submission against the GRID3 district master list (name matching, 116-district count), runs per-indicator range/type constraints, and produces the winsorization/distribution report. On success: promotes the submission to `published`, runs the scoring engine over the full dataset, writes results to the processed Postgres layer, and records the validation report in both the repo and the catalog entry (ADR-0015). On failure: marks the submission `rejected` with the reason in the catalog; the raw file is retained, never deleted. For v1, this pipeline is triggered manually via GitHub Actions `workflow_dispatch` (ADR-0012).

**Blocked by:** 03 — GRID3 client, 05 — Postgres schema and data I/O

**Status:** ready-for-agent

- [ ] Raw submission file is stored in the data lake location and a `pending` catalog entry is created
- [ ] Validation checks district names against the GRID3 master list and rejects on mismatch
- [ ] Validation enforces per-indicator range/type constraints
- [ ] Validation produces the winsorization/distribution report
- [ ] A fully passing run promotes the submission to `published`, scores via the scoring engine, and writes results to the processed layer
- [ ] A failing run marks the submission `rejected` with reason; the raw file is retained
- [ ] Validation report is recorded in both the repo (committed file) and the Postgres catalog entry
- [ ] End-to-end verifiable: submit a synthetic CSV, see it flow through to published scores in Postgres
