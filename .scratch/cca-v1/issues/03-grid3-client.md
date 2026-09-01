# 03 — GRID3 client

**What to build:** A module that fetches the 116-district master list (district name, district code, province, province code, and polygon boundary geometry as GeoJSON) from GRID3's ArcGIS FeatureServer and caches the result locally so it can be reused across the data-refresh cycle without hitting the API on every call. The cache is refreshed at each data-refresh cycle, not on every dashboard page load (ADR-0006).

**Blocked by:** 01 — Project scaffold

**Status:** ready-for-agent

- [ ] Module fetches the full 116-district dataset from the GRID3 FeatureServer endpoint
- [ ] Result is cached locally after fetch (not re-fetched on every use within a refresh cycle)
- [ ] Returns district name, code, province, province code, and GeoJSON polygon geometry per district
- [ ] Tested against a cached fixture (not the live endpoint) — confirms correct parsing of the expected 116 districts and their fields
