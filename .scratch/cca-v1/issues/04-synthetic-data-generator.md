# 04 — Synthetic data generator

**What to build:** A module that produces plausible fake indicator values across all 116 GRID3 districts and all 29 indicators, matching the sector/dimension/orientation metadata in `CCA_indicator_list.csv`. The output conforms to the scoring engine's input format so it can be fed straight through the pipeline. It deliberately includes some missing values (to exercise data-completeness logic) and some outlier values (to exercise winsorization). This is a first-class deliverable — the entire pipeline and dashboard are built and demoed against this synthetic data before real MoFNP data arrives.

**Blocked by:** 02 — Scoring engine, 03 — GRID3 client

**Status:** ready-for-agent

- [ ] Generates values for all 29 indicators across all 116 GRID3 districts (using real district names from the GRID3 client)
- [ ] Output conforms to the scoring engine's expected input format
- [ ] Includes deliberately missing indicator values for some districts (to trigger completeness flags)
- [ ] Includes outlier values for some indicators (to trigger winsorization capping)
- [ ] Feeding the output through the scoring engine produces valid Sector Index scores without errors
