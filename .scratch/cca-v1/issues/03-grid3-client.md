# 03 — GRID3 client

**What to build:** A module that fetches the 116-district master list (district name, district code, province, province code, and polygon boundary geometry as GeoJSON) from GRID3's ArcGIS FeatureServer and caches the result locally so it can be reused across the data-refresh cycle without hitting the API on every call. The cache is refreshed at each data-refresh cycle, not on every dashboard page load (ADR-0006).

**Blocked by:** 01 — Project scaffold

**Status:** done

- [x] Module fetches the full 116-district dataset from the GRID3 FeatureServer endpoint
- [x] Result is cached locally after fetch (not re-fetched on every use within a refresh cycle)
- [x] Returns district name, code, province, province code, and GeoJSON polygon geometry per district
- [x] Tested against a cached fixture (not the live endpoint) — confirms correct parsing of the expected 116 districts and their fields

## Comments

Implemented in `src/cca/grid3/client.py`:
- `FEATURESERVER_URL` — the exact GRID3 ArcGIS FeatureServer query from ADR-0006.
- `District` — frozen dataclass: name, code, province, province_code, geometry (GeoJSON dict).
- `parse_feature_collection` — pure parsing of a GeoJSON FeatureCollection into `District` records; no I/O.
- `fetch_district_master_list(cache_path, force_refresh=False, fetch_geojson=...)` — reads the local cache if present and `force_refresh` is not set; otherwise calls `fetch_geojson` (defaults to a `requests.get` against GRID3), writes the raw GeoJSON to `cache_path`, then parses it. `force_refresh=True` is the data-refresh-cycle path from ADR-0006; the no-refresh path is what the dashboard uses so a GRID3 outage can't take it down.

Added `requests>=2.31` to `pyproject.toml` as a new dependency for this adapter (the scoring engine itself stays dependency-free).

Tests in `tests/test_grid3_client.py` (7 cases) build a 116-feature GRID3-shaped GeoJSON fixture in-code (never hitting the live endpoint) and cover: parsing the full 116-district cohort with correct fields, fetch-and-cache-when-absent, cache-reuse-without-refetching, force-refresh overwriting an existing cache, and `District` hashability. Full repo suite: 34 passed.

`/code-review` caught two real bugs, both fixed:
- The cache was written *before* the fetched GeoJSON was parsed, so a malformed/schema-drifted GRID3 response would clobber the last-known-good cache before failing — defeating the whole point of caching against a GRID3 outage (ADR-0006). Now parse-then-write.
- `District` was a `frozen=True` dataclass with a `dict` geometry field, so the auto-generated `__hash__` would raise `TypeError` the moment a `District` went into a `set` or was used as a dict key. Added an explicit `__hash__` over the administrative fields only.
