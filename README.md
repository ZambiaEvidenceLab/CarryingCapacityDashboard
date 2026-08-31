# Multi-Index Carrying Capacity Assessment

## Background and rationale
The Ministry of Finances and National Planning wants a centralised methodology for assessing the "carrying capacity" of Zambian districts (116) of sustaining the needs of their population. 

The assessment would span 5 distinct sectors:
- health
- education
- agriculture
- infrastructure (water, electricity, ICTs)
- environment & demography

The Zambia Evidence Lab (ZEL) is proposing an index-based methodology that prioritises decision-making, and actionability. 

## Method
### Index
Each sector will have its own index. Indicators have been divided into two dimensions: **supply** and **access**. Each index will weight these two dimensions equally, regardless of the number of indicators inside of them. 

Importantly, all indicators have to be standardised (min-max, score out of 100), and oriented so that higher values indicates more capacity (e.g. nurses per capita is good as-is, but average distance to the nearest clinic would have to be inverted). Methodological choices (weighting, aggregation, normalisation) follow the OECD/JRC *Handbook on Constructing Composite Indicators* — see `docs/OECD_HANDBOOK_COMPOSITE_INDEX_GUIDANCE.md`.

Min-max is computed relative to the current 116-district cohort at each refresh, not against fixed benchmarks, and every refresh covers all 116 districts at once — see [ADR-0007](docs/adr/0007-relative-minmax-full-cohort.md). To stop one outlier district from compressing everyone else's scores, each indicator's raw values are winsorized (capped at the 1st/99th percentile) before min-max is applied, with an automated distribution check logged at every refresh — see [ADR-0008](docs/adr/0008-winsorize-before-minmax.md).

The Environment sector mixes ecological-condition indicators (forest cover, ecological diversity) with population-pressure indicators (population growth rate, cattle-head per capita, charcoal consumption); the pressure indicators are inverted so higher pressure lowers the index, consistent with the sector's own framing — see [ADR-0009](docs/adr/0009-environment-pressure-indicator-inversion.md) and the Notes column in `CCA_indicator_list.csv`.

Outcome indicators (e.g. mortality under 15 years old for the health sector) are excluded from the index math — see [ADR-0001](docs/adr/0001-exclude-outcome-indicators.md). They remain a candidate for future correlation analysis against the finished index.

The five Sector Indices are never combined into one overall district score — see [ADR-0002](docs/adr/0002-no-composite-score.md). Indicators are equally weighted within a dimension, and Supply/Access are equally weighted within a sector — see [ADR-0003](docs/adr/0003-equal-weighting.md).

Domain vocabulary (Sector, Dimension, Supply, Access, Indicator, Sector Index, etc.) is defined in `CONTEXT.md`.

### Data
A tentative list of indicators is provided in: CarryingCapacityDashboard\CCA_indicator_list.csv

*The sourcing of these indicators will be checked with the MoFNP.*

## Backend
Raw indicator data is never stored in PostgreSQL. It lives in a data lake, kept permanently and never overwritten once received — for now (development/prototyping), that means files on the developer's laptop and committed to this **private** repository; long-term, a proper data lake (cloud object storage or physical storage, still to be decided — see the workshop questions below) will replace this. PostgreSQL holds only the processed layer: the `indicators`, `indices`, and `metadata` schemas (cleaned indicator values and precomputed scores, which is what the dashboard actually reads), plus a lightweight catalog of raw submissions (file location, submitter, timestamp, status). See [ADR-0016](docs/adr/0016-raw-data-lake-interim-storage.md). Indicator values are stored with an effective date/period from the start, even though v1 of the dashboard only shows the latest snapshot — see [ADR-0004](docs/adr/0004-dated-values-snapshot-ui.md). Since indicators refresh on different cycles, each indicator's own reference year is shown alongside its value rather than implying every figure on screen is equally current.

Data intake for v1: an Excel/CSV update becomes a Raw Submission (a file in the data lake + a Postgres catalog entry) in a `pending` state. Because raw storage and the catalog can be written to outside this repository's own review process, the app never reads `pending` data directly — a validation pipeline (this repo's code, run manually via GitHub Actions for v1) checks it against the GRID3 district list, per-indicator ranges, and the ADR-0008 winsorization report, and only a fully passing run promotes it to `published` in Postgres, recomputes Sector Index scores, and redeploys the dashboard. A rejected submission's raw file is kept, not deleted — only the processed layer excludes it. See [ADR-0012](docs/adr/0012-database-gated-data-publish-pipeline.md). This is separate from app code deploys: merging a pull request to `main` auto-deploys code changes; a data promotion is its own independent trigger.

For now, the PostgreSQL database itself runs locally on the developer's laptop for development; where it (and the raw data lake) is hosted in production is an open workshop question — see below. This is all provisional pending the format MoFNP data actually arrives in, and pending the workshop discussion on who owns data verification and how hosting and handover work.

The canonical list of the 116 districts (names, codes, provinces, boundaries) — used both to validate uploads and to render the dashboard map — is queried live from GRID3's ArcGIS FeatureServer rather than stored as a local file, since it's the government-endorsed source and stays in sync if boundaries are ever revised. See [ADR-0006](docs/adr/0006-district-master-list-from-grid3.md).

## Dashboard
I imagine a map of Zambian districts. Upon clicking on one of them, we would get a spider chart (// radar chart) with the districts indices visualised against the district average.

From a district's radar chart, users can drill into any one sector axis to see a Decomposition View — the Dimension and Indicator scores behind that Sector Index — so someone who spots a low Health index can immediately see which underlying indicator(s) are driving it down (e.g. to prioritise investment). See `CONTEXT.md` for the Decomposition View definition.

Importantly, some districts are mostly Urban (e.g. Lusaka, Ndola). These district will have lower agriculture index values; this is normal and expected, and the dashboard need to make it clear to the user too — via a UI annotation, not an adjustment to the index math itself.

The landing page (before drilling into a district) shows a sector-selectable national choropleth map — pick a sector, see all 116 districts shaded by that Sector Index, and click through to a district's radar view from there — alongside a national summary strip for the selected sector (average score, spread, count of districts flagged for low data completeness).

There is also a need to have a clear explanation of the methodology available on the dashboard, structured as an FAQ at the bottom of the page covering two levels: general methodology (how a Sector Index is calculated, how Supply/Access combine, why scores are relative rather than fixed-benchmark) and per-indicator detail (which indicators feed which sector, and their data source).

Tech stack: Python + Dash — see [ADR-0005](docs/adr/0005-dash-dashboard-framework.md). The app itself does no calculation: Sector Index and indicator-level scores are precomputed during the data-refresh pipeline and the app only reads them — see [ADR-0010](docs/adr/0010-precompute-static-dashboard.md). Hosting is still open — see the workshop questions below.

## Open questions for the MoFNP workshop

The decisions above cover methodology and initial tech choices. The following are institutional questions that only MoFNP/the Planning team can resolve, to be worked through in a dedicated workshop before the data infrastructure is finalised.

### 1. Data ownership and collection
Who is responsible for collecting, compiling, and handing over indicator data for each sector — a single named focal point per ministry, or a function performed by whoever holds the M&E role at update time?

Possible routes:
- **A. Ministry-designated focal point** — one named person per line ministry owns their sector's data submission each cycle.
- **B. Centrally compiled by ZEL/MoFNP** — data pulled from existing reporting systems (HMIS, EMIS, LCMS) without creating a new role at each ministry.
- **C. Hybrid** — line ministries submit their own administrative-source data directly; ZamStats-sourced data (Census/LCMS) is pulled centrally by ZEL/MoFNP.

### 2. Data verification
What quality-check process happens before a submitted value is accepted into the database? Who is the "Verified By" person referenced in `CCA_indicator_list.csv`?

Possible routes:
- **A. Automated validation + manual sign-off** — range/outlier checks and district-name matching run automatically, then a named verifier signs off before ingest.
- **B. Automated validation only**, with a periodic (e.g. quarterly) manual audit sample.
- **C. Full manual review** of every submission by a central ZEL/MoFNP data team before each ingest cycle.

### 3. Database, data lake, and dashboard hosting
Where do the Postgres database, the raw data lake, and the dashboard actually run in production? This is currently unresolved even at the working-prototype level — for now, Postgres runs locally on a laptop and raw data lives in the private repository (see [ADR-0016](docs/adr/0016-raw-data-lake-interim-storage.md)), both explicitly interim. This decision needs to cover network access (can the automated validation pipeline reach the database and raw storage in production?) and access control (role separation between whoever loads raw data, the app's read-only access, and any admin access).

Possible routes:
- **A. Government-owned cloud account** (e.g. GCP, used before) — full Ministry data sovereignty, but requires a dedicated project and someone to administer it.
- **B. Hosted by ZEL or a partner**, with Ministry-granted access — faster to stand up, but data ownership/governance terms need to be made explicit in writing.
- **C. On-premises server at MoFNP** — maximum control, but requires in-house IT capacity for maintenance, backups, and uptime that may not currently exist.
- **D. A managed third-party cloud database** (e.g. DigitalOcean, AWS) rather than a full government cloud project — simpler to operate than (A), but raises the same data-sovereignty question as (B): who holds the account, who pays, and is a commercial cloud outside government control acceptable for this dataset.

Whichever route is chosen, the setup needs: encryption at rest and in transit, separate credentials for data-loading vs. the dashboard's read-only access, and — per the Ministry's plan to eventually own this infrastructure directly — a capacity-building plan so Ministry staff can operate and maintain it after handover (see Resourcing, below).

### 4. Update mechanism and cadence
How often does each sector refresh, and by what process does an update actually reach the database?

Possible routes:
- **A. Excel/CSV template per sector**, submitted on a fixed schedule aligned to each ministry's own reporting cycle (e.g. annual school census, HMIS periodicity), ingested via a validation script.
- **B. Shared Google Sheets per ministry** with a scheduled sync — lower friction for repeat updates, but requires Google Workspace access for every contributor.
- **C. A lightweight internal web form** built into the dashboard for direct entry — best long-term data-entry experience, but a larger build than needed for v1.

### 5. Resourcing
What ongoing commitment does the Ministry need to make to sustain this beyond the initial build?

Considerations to raise:
- A data steward/coordinator role (plausibly part-time) to chase ministry submissions each cycle.
- Cloud hosting costs — modest at this scale (one database + one dashboard app).
- Capacity-building for whoever at the Ministry ends up operating the PostgreSQL database directly (backups, access management, running the validation pipeline) once it's handed over.
- Ongoing developer/analyst time for maintenance, methodology updates, and adding indicators as data sourcing improves.
- In-house IT support if the on-premises hosting route is chosen.

### 6. Scope of the GitHub handover
Raw data itself is planned to be handed over via the PostgreSQL database directly (Section 3), with capacity-building for whoever operates it (Section 5). Separately, the validation/scoring code and its CI pipeline (see [ADR-0012](docs/adr/0012-database-gated-data-publish-pipeline.md)) live in this GitHub repository. Does responsibility for *that* repository also transfer to the Ministry — so Ministry-side (or ZEL-supporting) staff can trigger the validation pipeline, review its results, and eventually modify it — or does ZEL/a contractor retain ownership of the code indefinitely, with the Ministry only ever interacting with the database and the deployed dashboard?

Possible routes:
- **A. Whole-repository handover** (leaning towards this) — Ministry-side (or ZEL-supporting) staff get GitHub access: triggering the validation pipeline after loading new data, reviewing CI results, eventually maintaining the code. Requires some GitHub familiarity, or training, from whoever ends up in that role.
- **B. Database-and-dashboard-only handover** — the Ministry owns and operates the database and views the deployed dashboard, but ZEL or a contractor continues to own and run the validation/scoring code on the Ministry's behalf. Lower technical bar for Ministry staff, but creates an ongoing dependency on an external party for every data refresh.

### 7. Decisions the Planning team must make before proceeding
- Confirm the final indicator list per sector — several rows in `CCA_indicator_list.csv` have no confirmed source yet.
- Confirm data-sharing agreements with line ministries and ZamStats for indicators not already publicly available.
- Choose the hosting route (Section 3) and assign the budget/ownership it implies.
- Decide the update cadence per sector (Section 4) — likely constrained by each ministry's own reporting cycle rather than a single Ministry-wide schedule.
- Confirm who holds final sign-off authority on published index values before they go live on the dashboard.

