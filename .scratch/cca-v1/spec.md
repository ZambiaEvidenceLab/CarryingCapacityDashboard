Status: ready-for-agent

# Carrying Capacity Assessment — v1 Spec

## Problem Statement

The Ministry of Finance and National Planning (Zambia) needs a way to assess how much government capacity exists, per sector, to sustain the needs of each of the country's 116 districts. Today there is no centralised methodology or tool — sector data sits in separate ministries, in different formats, with no common scoring framework and no way for a decision-maker to compare districts or identify where investment is most needed within a sector.

## Solution

Build a district-level index system that scores five sectors (Health, Education, Agriculture, Infrastructure, Environment) independently for each of Zambia's 116 districts, displayed through an interactive dashboard. Each Sector Index is a 0–100 score derived from underlying Indicators, grouped into Supply and Access Dimensions (except Environment, which has no Dimensions). The dashboard lets users see all districts at a glance for a chosen sector, drill into any district's cross-sector profile, and decompose a low score to the specific Indicators driving it — directly informing where to prioritise resources.

## User Stories

1. As a **Ministry planner**, I want to select a sector and see all 116 districts shaded by their Sector Index on a map, so that I can immediately identify which districts are underserved in that sector.
2. As a **Ministry planner**, I want to click a district on the map and see a radar chart of its five Sector Index scores against the national average, so that I can see that district's relative strengths and weaknesses across sectors at a glance.
3. As a **Ministry planner**, I want to drill from a radar chart axis into a Decomposition View showing the Dimension and individual Indicator scores behind that Sector Index, so that I can trace a low score to the specific Indicators driving it and prioritise investment accordingly.
4. As a **Ministry planner**, I want to see a national summary strip (average score, spread, count of districts with low data completeness) for the selected sector alongside the map, so that I have a quick national-level context before drilling into individual districts.
5. As a **Ministry planner**, I want to see each Indicator's reference year displayed alongside its value, so that I understand how current each figure is — since Indicators within the same Sector Index may come from different reporting cycles.
6. As a **Ministry planner**, I want a clear visual annotation on districts that are mostly urban (e.g. Lusaka, Ndola), so that I understand their low Agriculture scores reflect urban land-use, not a failure of agricultural capacity.
7. As a **Ministry planner**, I want a data-completeness flag shown whenever a district's score was computed from fewer than the full set of Indicators, so that I know to treat that score with appropriate caution.
8. As a **Ministry planner**, I want an FAQ section on the dashboard explaining the methodology (how Sector Indices are calculated, how Supply/Access combine, why scores are relative rather than fixed-benchmark, which Indicators feed which sector and their data sources), so that I can trust and explain the scores.
9. As a **data steward**, I want to submit an Excel/CSV file of indicator values that enters the system in a `pending` state and must pass automated validation before it can affect the dashboard, so that bad data cannot corrupt published scores.
10. As a **data steward**, I want the validation pipeline to check district names against the GRID3 master list, enforce per-indicator range/type constraints, and produce a winsorization/distribution report, so that I have a clear, auditable reason for any acceptance or rejection.
11. As a **data steward**, I want rejected submissions to keep their raw file intact (never deleted), with the rejection reason recorded in the Postgres catalog, so that I can investigate and resubmit.
12. As a **data steward**, I want each pipeline run to write a new timestamped set of processed rows (append-only) rather than overwriting, so that I can see exactly which run produced the currently live scores.
13. As a **developer**, I want a synthetic data generator that produces plausible fake values across all 116 GRID3 districts and all 29 Indicators, so that the pipeline and dashboard can be built and demoed before real MoFNP data arrives.
14. As a **developer**, I want the scoring engine to be a single pure module with no database/network/file dependencies, so that I can run the full test suite in seconds with in-memory fixtures.
15. As a **developer**, I want the project set up with a Python virtual environment and a dependency file (`pyproject.toml` or `requirements.txt`), so that the environment is reproducible from the start.

## Implementation Decisions

### Scoring engine (pure module)

A single dependency-free Python module containing all CCA business logic. It accepts plain data (raw indicator values, the district master list, indicator metadata: weights, orientation, dimension mapping) and returns plain data (validation pass/fail + report, normalised indicator values, Sector Index scores, Decomposition View breakdown, data-completeness flags). No DB connection, no file I/O, no network calls inside.

The scoring engine implements:
- **Winsorization** at the 1st/99th percentile before normalisation, with a distribution report (min, max, mean, std, skew, which districts were capped) logged per indicator per run (ADR-0008).
- **Min-max normalisation** to [0, 100], recomputed over the full 116-district cohort each refresh — never partial (ADR-0007).
- **Orientation**: pressure indicators (population growth rate, cattle-head per capita, charcoal consumption) are inverted before normalisation so higher raw value = lower capacity (ADR-0009). Condition and supply/access indicators are left as-is.
- **Equal-weight aggregation**: Indicators averaged within a Dimension, Dimensions averaged within a Sector (ADR-0003). Environment has no Dimensions — its Indicators average directly to the Sector Index.
- **Data-completeness flagging**: when one or more Indicators are missing for a district in a given Dimension/Sector, the missing ones are dropped and the remainder re-averaged (not imputed), with a completeness flag attached.
- **Outcome Indicator exclusion**: outcome indicators are never fed into the scoring engine (ADR-0001). They exist in the indicator list for future correlation analysis only.

### GRID3 client

A module that fetches the 116-district master list (names, codes, provinces, boundaries as GeoJSON) from GRID3's ArcGIS FeatureServer. The result is cached at each data-refresh cycle — not on every dashboard page load — so that a GRID3 outage does not take the dashboard down (ADR-0006).

### Data pipeline and raw storage

Raw indicator submissions land in a data lake (interim: files on the developer's machine and committed to the private repo under a layout like `data/raw/<sector>/<date>-<submitter>.csv`). Each submission gets a Postgres catalog entry (`pending`/`published`/`rejected` status, submitter, timestamp, file location). The dashboard app never reads `pending` data (ADR-0012).

The validation pipeline (v1: triggered manually via GitHub Actions `workflow_dispatch`) is the only path from `pending` to `published`. A fully passing run promotes the data, feeds it through the scoring engine, writes the output to the processed Postgres layer, and records the validation report both in the repo and in the catalog entry (ADR-0015). A failing run marks the submission `rejected` with the reason; the raw file is always retained (ADR-0016).

Each successful pipeline run appends a new timestamped set of processed rows rather than overwriting (ADR-0014). The dashboard reads whichever run is marked current.

### Postgres schema

A single set of schemas shared across all five sectors (not per-sector tables), with a `sector` column:
- **`indicators` schema** — cleaned, normalised indicator values per district per indicator per run.
- **`indices` schema** — precomputed Sector Index and Dimension scores per district per run.
- **`metadata` schema** — indicator definitions, reference years, data-source attribution.
- **Catalog table** — one row per raw submission: file location, submitter, timestamp, status, validation report summary.

The dashboard app has read-only access. Data loading uses a separate credential.

### Dash dashboard

A Python/Dash app (ADR-0005) that performs no calculation at runtime (ADR-0010). It reads only from the processed Postgres layer. Views:
- **Landing page**: sector-selectable national choropleth map (all 116 districts shaded by the selected Sector Index) + national summary strip (average, spread, data-completeness count).
- **District view**: radar chart of the district's five Sector Index scores plotted against the national average.
- **Decomposition view**: reached by clicking a radar axis — shows that Sector's Dimension scores and individual Indicator scores, with reference years and data-completeness flags.
- **Urban annotation**: a UI note on districts classified as mostly urban, explaining lower Agriculture scores.
- **Methodology FAQ**: at the bottom of the page, covering general methodology and per-indicator detail.

### Synthetic data generator

A module that produces plausible fake indicator values across all 116 GRID3 districts and all 29 Indicators (matching the sector/dimension/orientation metadata in `CCA_indicator_list.csv`). This is a first-class deliverable — the pipeline, scoring engine, and dashboard are all built and demoed against synthetic data before real MoFNP data arrives. Synthetic values should be realistic enough to exercise the full normalisation/winsorization/completeness pipeline (including some deliberately missing values and some outliers that trigger winsorization).

### Project setup

The repo is set up with a Python virtual environment and a dependency/requirements file (`pyproject.toml` or `requirements.txt`) as part of standing up the scoring engine package. This is an explicit deliverable, not an assumed detail.

## Testing Decisions

The scoring engine is the testing focus. It contains all the logic that can produce a wrong score. Tests should exercise real scenarios that a developer would worry about:

- **Normalisation correctness**: given known raw values for 116 districts, do the normalised scores land where expected? Does a pressure indicator inversion actually flip the ranking?
- **Winsorization**: does an extreme outlier get capped at the 1st/99th percentile rather than stretching the scale?
- **Missing data**: when indicators are absent for some districts, are they dropped (not imputed), and does the completeness flag get set?
- **Environment sector**: no Dimensions — indicators average directly. Does it produce a different aggregation path from the four-sector Supply/Access pattern?
- **Full-cohort constraint**: the engine should reject partial-district input (fewer than 116 districts without explicit justification).

Tests use in-memory fixtures — plain dicts/DataFrames of fake indicator values. No database, no file I/O, no mocking of external services.

Adapters (GRID3 client, Postgres I/O, Dash app) get light integration-level tests only — enough to confirm the wiring works (e.g. the GRID3 client parses a cached fixture correctly; the Dash app can load and shape a row for the map view). Do not duplicate the scoring engine's coverage at the adapter boundary.

The synthetic data generator is tested indirectly: if it produces data that the scoring engine processes without errors and the dashboard renders without blanks, it's working. No separate unit tests for the generator's internal randomisation.

## Out of Scope

- **Historical/trend views**: the v1 dashboard shows only the latest Snapshot. Dated values are stored from day one (ADR-0004), but no time-series UI is built yet.
- **Composite score**: the five Sector Indices are never combined into a single overall district score (ADR-0002).
- **Fixed benchmarks**: normalisation is relative to the 116-district cohort, not against externally set targets (ADR-0007). Revisitable once MoFNP defines per-indicator targets.
- **Production hosting decisions**: where Postgres, the data lake, and the dashboard run in production is an open MoFNP workshop question. The architecture is designed so this can be decided later without changing code.
- **Data ownership/verification roles**: who submits and signs off per ministry is a workshop question. The pipeline enforces validation regardless of who triggers it.
- **Web-form data entry**: v1 uses Excel/CSV submission, not a built-in data-entry UI.
- **Outcome Indicator correlation analysis**: tracked as a future use case, not built in v1.
- **Automated pipeline triggering**: v1 uses manual `workflow_dispatch`; no database webhooks or polling.

## Further Notes

- Domain vocabulary is defined in `CONTEXT.md` — all code, UI labels, and documentation should use these exact terms (Sector, Dimension, Supply, Access, Indicator, Outcome Indicator, Sector Index, District, Snapshot, Decomposition View, Raw Submission, Data completeness).
- The indicator list in `CCA_indicator_list.csv` is tentative — several rows lack a confirmed data source. The architecture handles this gracefully: missing indicators are dropped per the data-completeness logic, not imputed.
- ADRs 0001–0016 (skipping superseded ones in favour of their replacements) are the authoritative record of methodology and architecture decisions. The spec does not duplicate their full rationale — read the relevant ADR when implementing a specific decision.
- The OECD/JRC Handbook (`docs/OECD_HANDBOOK_COMPOSITE_INDEX_GUIDANCE.md`) is the methodological reference underpinning the normalisation, weighting, and aggregation choices.
