# 03 — DMC app shell, map-hero layout, and WebGL map

**What to build:** The v2 skeleton and the fast map. Rebuild the dashboard shell
on dash-mantine-components (ADR-0018) in the **map-hero** layout — a large map on
the left (~60–65%) with a column reserved for the ranked list on the right (a
placeholder until ticket 04) — replacing v1's stacked `html`/`dcc` tree. Switch
the choropleth to `go.Choroplethmap` (WebGL, plotly 7) with **no external
basemap** (blank background, no reliance on internet tiles), a **distinct
sequential hue per Sector** (dark = high capacity), and colour **shaded across
the selected measure's live min–max**, not a fixed 0–100 (ADR-0017, levers 2–3;
see the spec's colour section). Selecting a Sector re-hues the map. A dynamic
one-line subtitle states the current Sector and the colour direction/range.

The map+list+drawer **interaction model** is now validated (map-hero won over
list-hero / KPI-band in the prototype) — write its ADR as part of this ticket.

The prototype (`.scratch/cca-v2/prototype/app.py`) encodes the trace config,
per-Sector ramps, dynamic `zmin`/`zmax`, and `Patch()`-based recolour scaffold.

**Blocked by:** 01 (deps + simplified boundaries).

**Status:** ready-for-agent

- [ ] The page renders in a DMC `AppShell` — header (title, subtitle, a
      Methodology link) and a main area with the Sector control, map, and a
      right-hand column placeholder.
- [ ] The map is `go.Choroplethmap`, WebGL, no basemap, all 116 Districts, and
      feels responsive on a laptop.
- [ ] Each Sector has its own single-hue light→dark ramp; dark = high capacity;
      switching Sector re-hues the map.
- [ ] Colour is scaled to the displayed measure's actual min–max; the subtitle
      names the Sector and the range shown.
- [ ] A new ADR records the map-hero + drawer interaction model (extends ADR-0005
      / ADR-0018).
- [ ] The five Sector hue anchors are run through the dataviz CVD validator
      (`scripts/validate_palette.js`) and adjusted if any pair fails.
