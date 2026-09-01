# 07 — Dash dashboard

**What to build:** The interactive Python/Dash application (ADR-0005) that surfaces all precomputed CCA scores to Ministry planners. The app performs no calculation at runtime (ADR-0010) — it reads only from the processed Postgres layer.

**Landing page:** A sector-selectable national choropleth map showing all 116 districts shaded by the selected Sector Index, rendered using the GRID3 GeoJSON boundaries. Alongside the map, a national summary strip for the selected sector (average score, spread, count of districts flagged for low data completeness).

**District view:** Clicking a district on the map opens a radar chart of that district's five Sector Index scores plotted against the national average, giving a cross-sector profile at a glance.

**Decomposition view:** Clicking a radar chart axis drills into that Sector's Dimension and individual Indicator scores, with each Indicator's reference year shown alongside its value and data-completeness flags where applicable.

**Urban annotation:** Districts classified as mostly urban (e.g. Lusaka, Ndola) get a UI annotation explaining that lower Agriculture scores reflect urban land-use, not a capacity failure.

**Methodology FAQ:** At the bottom of the page, an FAQ covering general methodology (how Sector Indices are calculated, how Supply/Access combine, why scores are relative) and per-indicator detail (which Indicators feed which Sector, their data sources).

**Blocked by:** 03 — GRID3 client, 05 — Postgres schema and data I/O

**Status:** ready-for-agent

- [ ] Landing page shows a sector-selectable choropleth map of 116 districts, shaded by Sector Index
- [ ] National summary strip displays average score, spread, and data-completeness count for the selected sector
- [ ] Clicking a district opens a radar chart of its five Sector Index scores against the national average
- [ ] Clicking a radar axis opens the Decomposition View showing Dimension and Indicator scores with reference years
- [ ] Data-completeness flags are visible where a score was computed from incomplete Indicators
- [ ] Urban districts display an annotation explaining lower Agriculture scores
- [ ] Methodology FAQ is present at the bottom of the page
- [ ] The app performs no calculation — all scores are read from the processed Postgres layer
