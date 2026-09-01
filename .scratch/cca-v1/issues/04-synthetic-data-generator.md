# 04 — Synthetic data generator

**What to build:** A module that produces plausible fake indicator values across all 116 GRID3 districts and all 29 indicators, matching the sector/dimension/orientation metadata in `CCA_indicator_list.csv`. The output conforms to the scoring engine's input format so it can be fed straight through the pipeline. It deliberately includes some missing values (to exercise data-completeness logic) and some outlier values (to exercise winsorization). This is a first-class deliverable — the entire pipeline and dashboard are built and demoed against this synthetic data before real MoFNP data arrives.

**Blocked by:** 02 — Scoring engine, 03 — GRID3 client

**Status:** done

- [x] Generates values for all 29 indicators across all 116 GRID3 districts (using real district names from the GRID3 client)
- [x] Output conforms to the scoring engine's expected input format
- [x] Includes deliberately missing indicator values for some districts (to trigger completeness flags)
- [x] Includes outlier values for some indicators (to trigger winsorization capping)
- [x] Feeding the output through the scoring engine produces valid Sector Index scores without errors

## Comments

Implemented in `src/cca/synthetic/generator.py`:
- `INDICATOR_RANGES` — a plausible raw-value range (`IndicatorRange(low, high)`) per Indicator ID, mirroring `CCA_indicator_list.csv`'s units.
- `generate_synthetic_indicators(district_codes, indicator_metas, seed=, missing_rate=, outlier_rate=)` — draws a uniform value per (district, indicator) from its range, then removes `missing_rate` of cells and pushes `outlier_rate` of cells 3-6x their indicator's span past its bounds. `max(1, round(...))` guarantees at least one missing and one outlier cell whenever a rate is positive, regardless of cohort size. Returns a `district_code`/`indicator_id`/`value` DataFrame — the scoring engine's expected input format.
- `generate_synthetic_dataset(districts, ...)` — convenience wrapper taking real `cca.grid3.client.District` records and defaulting to the canonical `CCA_INDICATORS` catalog.

Tests in `tests/test_synthetic_generator.py` (7 cases): format/coverage checks on the low-level generator, an unknown-indicator rejection, GRID3-`District` wiring, and — per the spec's testing philosophy for this module ("tested indirectly... no separate unit tests for the generator's internal randomisation") — three integration cases that feed generated data through `run_scoring` and assert it produces valid Sector Index scores, some incomplete scores from the injected missing values, and winsorization capping from the injected outliers. Full repo suite: 41 passed.

`/code-review` (Standards + Spec axes) findings and how they were handled:
- **Fixed** — the ticket's "using real district names from the GRID3 client" requirement wasn't wired up; `generate_synthetic_dataset` took raw strings. Now takes `list[District]` directly.
- **Fixed** — several tests unit-tested the generator's own randomisation (missing-rate/outlier-rate behaviour in isolation), which the spec explicitly asks to avoid for this module. Removed; that behaviour is now only asserted indirectly via the `run_scoring` integration tests.
- **Noted, not fixed here (pre-existing, ticket 02 scope)** — `CCA_INDICATORS` defines 28 indicators, not the 29 the ticket/spec reference. `INDICATOR_RANGES` mirrors the catalog exactly, so the generator is internally consistent; the count mismatch is upstream in `src/cca/scoring/indicators.py`.
- Standards judgement calls (local wrapper import, param echo between the two public functions, mutation-based row construction vs. the engine's vectorized pandas style) were left as-is — each is a minor, non-blocking stylistic nit.
