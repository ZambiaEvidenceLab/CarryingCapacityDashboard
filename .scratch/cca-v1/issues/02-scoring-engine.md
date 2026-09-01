# 02 — Scoring engine

**What to build:** A single pure Python module containing all CCA business logic. It accepts plain data (raw indicator values as a DataFrame/dict, the 116-district master list, and indicator metadata — weights, orientation, dimension mapping) and returns plain data (validation pass/fail, winsorization report, normalised indicator values, Sector Index scores, Decomposition View breakdown, and data-completeness flags). No database, file I/O, or network calls inside — fully testable with in-memory fixtures.

The module implements: winsorization at 1st/99th percentile with a per-indicator distribution report (ADR-0008); min-max normalisation to [0, 100] over the full 116-district cohort (ADR-0007); orientation inversion for pressure indicators (ADR-0009); equal-weight aggregation of Indicators within Dimensions and Dimensions within Sectors, with Environment averaging Indicators directly (ADR-0003); and data-completeness flagging when Indicators are missing for a district (dropped, not imputed).

**Blocked by:** 01 — Project scaffold

**Status:** done

- [x] Scoring engine module exists as a dependency-free package (no DB/IO/network imports)
- [x] Winsorization caps values at 1st/99th percentile and produces a distribution report per indicator
- [x] Min-max normalisation produces [0, 100] scores recomputed over the full district cohort
- [x] Pressure indicators (Environment sector) are inverted before normalisation
- [x] Equal-weight aggregation works for both the Supply/Access Dimension path and Environment's dimension-less path
- [x] Missing indicators are dropped and re-averaged, with a completeness flag set on the affected district/dimension
- [x] Tests cover: normalisation correctness with known values, winsorization capping, pressure-indicator inversion, missing-data handling, and Environment's aggregation path

## Comments

Implemented in `src/cca/scoring/engine.py`:
- `validate_full_cohort` — rejects a submission unless every master-list district is represented (ADR-0007); `allow_partial=True` is the explicit override the spec calls for.
- `winsorize` — caps at 1st/99th percentile, returns a pre/post distribution report (min/max/mean/std/skew) plus which districts were capped (ADR-0008).
- `orient` / `normalise` — orientation inversion (ADR-0009) applied before min-max scaling to [0, 100] (ADR-0007).
- `aggregate` — equal-weight average of present indicator scores; missing ones are dropped (not imputed), with a completeness flag when the used/total count differs.
- `run_scoring` — full pipeline: validates the cohort, scores every indicator, then aggregates into `dimension_scores` (Supply/Access path) and `sector_scores` (Environment's indicators average directly into the sector row, no dimension rows produced).
- `decomposition_view` — traces one district's Sector Index down to Dimension and Indicator-level scores.

Tests in `tests/test_scoring_engine.py` (21 cases) cover full-cohort validation (pass/reject/override/unknown-district/duplicate-rows), normalisation (including cohort-size sensitivity and constant/missing values), orientation inversion, winsorization capping and its distribution report, aggregation with missing data, the Supply/Access sector path, the Environment dimension-less path, and the Decomposition View. Full repo test suite: 22 passed.
