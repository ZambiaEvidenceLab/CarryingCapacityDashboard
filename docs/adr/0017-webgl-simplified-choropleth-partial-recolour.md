---
status: accepted
---

# Tile-less WebGL choropleth with pre-simplified boundaries and partial recolour

The v1 map rendered all 116 districts with `go.Choropleth` (SVG paths) from the full-resolution GRID3 boundaries — ~32.9 MB and ~847k vertices — and rebuilt the whole figure, re-attaching the entire GeoJSON, on every sector change. That is the source of the map's clunkiness. v2 attacks all three causes:

1. **Pre-simplify the boundaries at data-refresh time, not page load.** The GRID3 geometry is simplified (Douglas–Peucker, topology-preserving, ~1–2% tolerance) down to the order of ~13k vertices / a few hundred KB, and stored alongside the boundary cache. This is a build/refresh step, consistent with [ADR-0010](0010-precompute-static-dashboard.md) (the running app performs no calculation) and with [ADR-0006](0006-district-master-list-from-grid3.md) caching GRID3 at refresh rather than per page load. District identity is unaffected — only vertex density drops.
2. **Render with `go.Choroplethmap` (WebGL) and no basemap.** Plotly 7's MapLibre-backed trace replaces the SVG `go.Choropleth`. The map style is a blank background (`white-bg`) with **no external tile layer**, so the app never depends on internet map tiles inside a Ministry network and keeps the clean borders-only look — while still getting WebGL rendering instead of hundreds of thousands of DOM paths.
3. **Recolour via partial property updates, never a figure rebuild.** Changing Sector or the Supply/Access measure updates only the `z` score array (and the colourbar) through Dash's `Patch()` class. The boundary geometry is serialised to the browser once, on first render, not resent on every interaction — the single biggest perceived-speed win over v1.

Trade-off accepted: simplified boundaries are visually coarser than full resolution (immaterial at national zoom, and the map is a locator, not a cadastral tool), and dropping a basemap means no roads/rivers for orientation (deliberate — province borders and district shapes are the only context a national capacity scan needs, and it removes an external dependency). Reversible in principle, but the simplification pipeline and the WebGL trace choice are enough of a commitment, and surprising enough to a future reader ("why is the geometry lossy / why no map tiles?"), to record here.
