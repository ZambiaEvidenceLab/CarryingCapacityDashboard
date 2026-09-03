Status: ready-for-agent

# Carrying Capacity Assessment — v2 Dashboard Refinement Spec

## Problem Statement

The v1 dashboard (`.scratch/cca-v1/`) is a faithful implementation of the v1
spec but a barebones one: raw Dash `html`/`dcc` components, a slow SVG
choropleth, and a scroll-down-forever interaction model (click district →
scroll → click radar axis → scroll). It works, but it is not decision-grade for
its real user and it is not quick.

The user is **Ministry of Finance and National Planning (MoFNP) staff allocating
budget or staffing across Zambia's 116 districts**. The dashboard must be
**quick** (the map is currently clunky), **uncluttered** (tell just enough), and
**guide just enough** to let the data speak. This v2 refines the existing
dashboard toward that bar without changing the underlying data model or
methodology (all ADRs 0001–0016 stand; no composite score, no fixed benchmarks).

## Primary Job (settled)

The dashboard's hero job is **within-sector prioritisation**: "For this sector's
budget, which districts are most underserved, and is the gap on the Supply side
or the Access side?" National scan → ranked priorities → (secondary) drill into
one district's cross-sector profile.

## Settled Decisions

These were reached by a full grilling pass. Each is fixed for v2.

### Interaction model & layout (desktop-first)

- **Desktop-first**, gracefully usable on a laptop, and **legible when projected
  in a workshop** (large type, high contrast, never rely on hover alone). Full
  mobile responsiveness is explicitly deferred.
- **Component library: dash-mantine-components (DMC).** Use its layout
  primitives (`AppShell`, `Grid`, `Drawer`, `SegmentedControl`, `Tabs`) rather
  than hand CSS. Adds a dependency; pin it in `pyproject.toml`.
- **One-screen national scan**: map on the left (~60%), a **ranked district
  list** on the right (~40%), the two **linked** — hovering/selecting a district
  highlights it in both. The ranked list is the primary priority carrier (see
  colour note below); the map answers "are the priorities geographically
  clustered?"
- **Within-district detail lives in a right-side `Drawer`** that slides in over
  the scan when a district is selected; the scan stays put underneath. The radar
  chart (district vs national average) and the Decomposition View stack
  vertically inside the drawer. Closing the drawer returns the user to the scan
  with their place intact. This replaces v1's stacked `district-section` /
  `decomposition-section` divs.
- **The Decomposition View opens by default** (prototype-validated) — it renders
  immediately for the sector currently shown on the map, without a second click.
  Clicking a radar axis (or a sector selector inside the drawer) switches which
  sector is decomposed. v1's "must click a radar axis to see anything" step is
  removed.

### Supply vs Access

- A **`SegmentedControl` above the map: `Overall · Supply · Access`**. Switching
  recolours the map **and** re-ranks the list, reframing "underserved" as an
  overall / supply-gap / access-gap question in one click.
- **Environment has no Dimensions** (ADR: Environment indicators average
  directly to the Sector Index). When the selected sector is Environment, the
  Supply/Access control is **hidden or disabled** — only Overall applies.
- **A "what's in Supply / Access?" hover next to the control** (prototype-
  validated) lists the current sector's Supply and Access Indicators without
  drilling into a district. This is the quick, in-place answer; the full
  per-indicator detail still lives in Methodology and the decomposition.

### Map performance ("make it QUICK") — all three levers

1. **Simplify the geometry.** The GRID3 boundary set is 32.9 MB / ~847k vertices
   at full precision. Simplify (e.g. mapshaper Visvalingam to ~1–2%) to the order
   of ~15k vertices as a **build-time/data-refresh step**, not at page load. Keep
   the simplified GeoJSON alongside the cache. Target a payload in the low
   hundreds of KB.
2. **Switch the trace to WebGL.** Replace `go.Choropleth` (SVG paths) with
   `go.Choroplethmap` (plotly 7, MapLibre/WebGL). Use **no external basemap**
   (white/blank background) so the app never depends on internet map tiles inside
   a Ministry network, and the clean borders-only look is preserved.
3. **Stop re-sending boundaries on recolour.** Send the geometry to the browser
   **once**. On sector / Supply-Access change, update only the `z` score array
   (and colourbar title) via Dash `Patch()` — `patched["data"][0]["z"] = …` —
   never rebuild the figure with `geojson=` re-attached (v1's `compute_map_figure`
   re-attaches the full GeoJSON on every dropdown change; this is the single
   biggest perceived-speed regression).

### Colour semantics (dataviz skill applied; prototype-validated)

- Each sector map is a **sequential single-hue** ramp, light→dark. **No rainbow,
  no diverging** (there is no principled midpoint — scores are relative min-max
  over the 116-district cohort).
- **A distinct hue per sector** (prototype: Health red · Education blue ·
  Agriculture green · Infrastructure purple · Environment amber), for wayfinding
  when switching sectors. Only one sector's map is shown at a time, so the hues
  never sit adjacent in one view. **Still to do: run the five hue anchors through
  the dataviz CVD validator** (`scripts/validate_palette.js` — needs Node, absent
  in the prototype environment).
- **Dark = high capacity** (intuitive for a *carrying-capacity* index), pale =
  more underserved. The **legend/subtitle states the direction explicitly**.
- **Shade across the sector's live min–max, not a fixed 0–100** (`zmin`/`zmax`
  set to the displayed measure's actual range). A Sector Index is the *average*
  of several 0–100 indicators, so its cross-district spread is genuinely narrower
  than 0–100 (this is also why the national average is not 50); pinning colour to
  0–100 washes the map out even on correct data. Dynamic range is consistent with
  the "scores are relative to the cohort" rule (ADR-0007). The subtitle names the
  range shown (e.g. "shaded across this sector's range, 12–88").

### Ranked district list

- Each row: **rank · district name · score (with a small inline microbar) · a
  data-completeness dot · an "Urban" chip where relevant**.
- **Default sort: ascending (worst-served first)** — that is the budget question
  answered on load. Sortable.
- Keep it lightweight in DMC first. Only introduce `dash-ag-grid` later if heavy
  column filtering is genuinely needed; do not add it pre-emptively.

### Decomposition figures — raw values, not just scores (prototype-validated)

The decomposition must show, per Indicator:

- **The raw value with its unit** (e.g. "12.3 per 10k"), alongside the 0–100
  normalised score. Ministry users need the actual figure, not only the relative
  score.
- **A compare-to-others chart** — a strip/distribution of all 116 districts on
  that Indicator's raw value, with *this* district highlighted and the others
  greyed, plus the **national average** line. This shows not just "how low" but
  "how low relative to peers."
- **An optional objective/threshold line** on the same chart, in raw units,
  ready to hold a **National Development Plan target** for that Indicator once
  MoFNP supplies them (stubbed until then).

**Data dependency — this needs a data-model change (see Decision records).**
The processed layer currently stores only *normalised* Indicator values, and
ADR-0016 states raw values never live there. Raw figures + raw-unit objective
lines cannot be served without persisting the numeric raw value per Indicator in
the processed layer and exposing (a) a district's raw values and (b) the
cohort-wide values for one Indicator to the read-only dashboard. This revisits
ADR-0016 and is its own pipeline/storage work item, upstream of the UI.

### Data-completeness & urban treatment

- **Completeness**: an amber dot on the list row **and** a subtle hatch/stipple
  overlay on that district on the map, with a hover/label explanation. Rationale:
  a user must not act on a dark (high-capacity) district that is dark only
  because half its Indicators are missing. (v1 shows only a top-level count.)
- **Urban**: a small "Urban" chip on the row and in the drawer. The Agriculture
  land-use explanation surfaces **only when the selected sector is Agriculture**
  (contextual, not always-on noise).

### Methodology / FAQ placement

- **Split** (v1 dumps it all at the page bottom):
  - **Per-indicator detail** (what the Indicator is, reference year, data source)
    appears **contextually in the Decomposition drawer** — info icons next to
    each Indicator, answering the question where it arises.
  - **General methodology** (how Sector Indices are computed, Supply/Access
    aggregation, why scores are relative) lives behind a **"Methodology" link in
    the header** that opens a drawer/modal — one click away, out of the way.

### Guidance & states

- **"Guide just enough"**: a **dynamic one-line subtitle** under the title that
  reflects the current sector/segment and states the colour direction (e.g.
  "Showing Health — Access. Darker = more capacity. Click a district for
  detail."), plus tooltips on controls. Optionally a **single dismissible intro
  card** on the very first visit (scan → rank → drill). **No stepped guided
  tour.**
- **Explicit empty/error/loading states**: DB-unreachable → a clear banner
  ("Data unavailable, contact …"); a district with no score → greyed on the map +
  "No data" in the list; loading affordance (spinner/skeleton) on callbacks,
  because even after the speed fixes the first map paint has some cost.

## Constraints (unchanged from v1)

- **No runtime calculation** (ADR-0010) — the dashboard still only reads the
  processed Postgres layer and reshapes. Geometry simplification is a
  build/refresh step, not a page-load step.
- **No composite score** (ADR-0002); **relative min-max**, not fixed benchmarks
  (ADR-0007).
- **Domain vocabulary** (`CONTEXT.md`) — Sector, Dimension, Supply, Access,
  Indicator, Sector Index, District, Decomposition View, Data completeness — used
  verbatim in all UI labels.
- **Never `git commit`** in this repo (CLAUDE.md) — propose the message, the user
  commits.

## Approach

Prototype-first, and **the prototype is done and validated** (see
`.scratch/cca-v2/prototype/` — a throwaway DMC app on synthetic in-memory data).
It confirmed the **map-hero** layout (map big-left, ranked list right, detail in
a right drawer), the WebGL no-tile map, the per-sector hues + live-range
shading, the Patch recolour, the decomposition-open-by-default, the raw-value +
compare-to-others indicator charts, and the Supply/Access hover legend. The
remaining work is porting this validated structure into `src/cca/dashboard/`
(`layout.py`, `callbacks.py`, `data.py`) plus the one upstream data-model change
raw values require — sequenced as the tickets under `issues/`.

## Decision records

Grilling + prototype decisions that met the ADR bar (hard to reverse, surprising
without context, a real trade-off) are recorded:

- **ADR-0017** — tile-less WebGL choropleth with pre-simplified boundaries and
  `Patch()` recolour (the "make it QUICK" architecture; extends ADR-0010).
- **ADR-0018** — dash-mantine-components as the UI component library (extends
  ADR-0005).

**Now ready to write (were deferred pending the prototype):**

- The **map-hero + drawer interaction model** — validated (variant A won over
  list-hero / KPI-band). Write its ADR as part of the layout ticket.
- **Raw Indicator values in the processed layer** — persisting the numeric raw
  value per Indicator to serve the decomposition's actual figures and raw-unit
  objective lines. This **revisits ADR-0016** ("raw values never live in the
  processed layer"); the revisit distinguishes the raw *submission files* (still
  never in the processed layer) from the numeric raw *value* the dashboard needs.
  Write a new ADR (superseding/amending 0016) as part of that ticket.

Colour orientation (dark = high capacity), per-sector hues, live-range shading,
and the Supply/Access toggle are cheap to reverse and live in this spec, not an
ADR.

## Out of Scope (for v2)

- Historical / trend views (ADR-0004 — still latest-Snapshot only).
- Composite score, fixed benchmarks, outcome-indicator correlation.
- Full mobile responsiveness.
- Any change to the **scoring engine** or **scoring methodology** (winsorize /
  min-max / aggregation are untouched). The one data-layer change in scope is
  *persisting* raw Indicator values for display — it does not alter how any score
  is computed.
- `dash-ag-grid` (deferred unless heavy filtering proves necessary).
