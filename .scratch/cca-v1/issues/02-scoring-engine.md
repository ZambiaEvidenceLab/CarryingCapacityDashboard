# 02 — Scoring engine

**What to build:** A single pure Python module containing all CCA business logic. It accepts plain data (raw indicator values as a DataFrame/dict, the 116-district master list, and indicator metadata — weights, orientation, dimension mapping) and returns plain data (validation pass/fail, winsorization report, normalised indicator values, Sector Index scores, Decomposition View breakdown, and data-completeness flags). No database, file I/O, or network calls inside — fully testable with in-memory fixtures.

The module implements: winsorization at 1st/99th percentile with a per-indicator distribution report (ADR-0008); min-max normalisation to [0, 100] over the full 116-district cohort (ADR-0007); orientation inversion for pressure indicators (ADR-0009); equal-weight aggregation of Indicators within Dimensions and Dimensions within Sectors, with Environment averaging Indicators directly (ADR-0003); and data-completeness flagging when Indicators are missing for a district (dropped, not imputed).

**Blocked by:** 01 — Project scaffold

**Status:** ready-for-agent

- [ ] Scoring engine module exists as a dependency-free package (no DB/IO/network imports)
- [ ] Winsorization caps values at 1st/99th percentile and produces a distribution report per indicator
- [ ] Min-max normalisation produces [0, 100] scores recomputed over the full district cohort
- [ ] Pressure indicators (Environment sector) are inverted before normalisation
- [ ] Equal-weight aggregation works for both the Supply/Access Dimension path and Environment's dimension-less path
- [ ] Missing indicators are dropped and re-averaged, with a completeness flag set on the affected district/dimension
- [ ] Tests cover: normalisation correctness with known values, winsorization capping, pressure-indicator inversion, missing-data handling, and Environment's aggregation path
