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

Outcome indicators (e.g. mortality under 15 years old for the health sector) are excluded from the index math — see [ADR-0001](docs/adr/0001-exclude-outcome-indicators.md). They remain a candidate for future correlation analysis against the finished index.

The five Sector Indices are never combined into one overall district score — see [ADR-0002](docs/adr/0002-no-composite-score.md). Indicators are equally weighted within a dimension, and Supply/Access are equally weighted within a sector — see [ADR-0003](docs/adr/0003-equal-weighting.md).

Domain vocabulary (Sector, Dimension, Supply, Access, Indicator, Sector Index, etc.) is defined in `CONTEXT.md`.

### Data
A tentative list of indicators is provided in: CarryingCapacityDashboard\CCA_indicator_list.csv

*The sourcing of these indicators will be checked with the MoFNP.*

## Backend
Data will be hosted in a PostgreSQL database. Indicator values are stored with an effective date/period from the start, even though v1 of the dashboard only shows the latest snapshot — see [ADR-0004](docs/adr/0004-dated-values-snapshot-ui.md). Since indicators refresh on different cycles, each indicator's own reference year is shown alongside its value rather than implying every figure on screen is equally current.

Data intake for v1: Excel/CSV upload with a validation script, matching how ministry staff already work. This is provisional pending the format MoFNP data actually arrives in, and pending the workshop discussion below.

The canonical list of the 116 districts (names, codes, provinces, boundaries) — used both to validate uploads and to render the dashboard map — is queried live from GRID3's ArcGIS FeatureServer rather than stored as a local file, since it's the government-endorsed source and stays in sync if boundaries are ever revised. See [ADR-0006](docs/adr/0006-district-master-list-from-grid3.md).

## Dashboard
I imagine a map of Zambian districts. Upon clicking on one of them, we would get a spider chart (// radar chart) with the districts indices visualised against the district average. 

Importantly, some districts are mostly Urban (e.g. Lusaka, Ndola). These district will have lower agriculture index values; this is normal and expected, and the dashboard need to make it clear to the user too — via a UI annotation, not an adjustment to the index math itself.

We also need some top-level analysis before someone clicks on the districts. 

There is also a need to have a clear explanation of the methodology available on the dashboard. 

Tech stack: Python + Dash — see [ADR-0005](docs/adr/0005-dash-dashboard-framework.md). Hosting is still open — see the workshop questions below.

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

### 3. Database hosting
Where does the Postgres database and dashboard actually run?

Possible routes:
- **A. Government-owned cloud account** (e.g. GCP, used before) — full Ministry data sovereignty, but requires a dedicated project and someone to administer it.
- **B. Hosted by ZEL or a partner**, with Ministry-granted access — faster to stand up, but data ownership/governance terms need to be made explicit in writing.
- **C. On-premises server at MoFNP** — maximum control, but requires in-house IT capacity for maintenance, backups, and uptime that may not currently exist.

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
- Ongoing developer/analyst time for maintenance, methodology updates, and adding indicators as data sourcing improves.
- In-house IT support if the on-premises hosting route is chosen.

### 6. Decisions the Planning team must make before proceeding
- Confirm the final indicator list per sector — several rows in `CCA_indicator_list.csv` have no confirmed source yet.
- Confirm data-sharing agreements with line ministries and ZamStats for indicators not already publicly available.
- Choose the hosting route (Section 3) and assign the budget/ownership it implies.
- Decide the update cadence per sector (Section 4) — likely constrained by each ministry's own reporting cycle rather than a single Ministry-wide schedule.
- Confirm who holds final sign-off authority on published index values before they go live on the dashboard.

