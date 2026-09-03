# 06 — District drawer: radar and Decomposition View open by default

**What to build:** The within-District detail, in a right-side `Drawer` that
slides in over the scan (which stays put underneath) when a District is selected.
The drawer shows the radar chart of the District's five Sector Index scores
against the national average, and — the key v1 fix — the **Decomposition View
open by default**, rendered immediately for the Sector currently shown on the
map. No second click is needed to see anything. Clicking a radar axis (or a
Sector selector in the drawer) switches which Sector is decomposed. Each
Indicator row shows its reference year, data source, and a data-completeness flag
where applicable. The Urban land-use note appears for mostly-urban Districts, and
is surfaced against Agriculture specifically.

(Indicator raw figures + the compare-to-others chart are ticket 07 — this ticket
delivers the drawer, radar, and the score-level decomposition.)

**Reuse from the prototype** (`.scratch/cca-v2/prototype/app.py`):
`build_radar_figure`, the `_open_detail` drawer structure (radar + decomposition
built inline so it shows by default), `_axis_to_sector`, and the score-level part
of `decomposition_cards`. Replace synthetic reads with the processed-layer
decomposition read; do not port any scoring.

**Blocked by:** 04 (District selection).

**Status:** done

- [x] Selecting a District opens the right drawer with the radar (District vs
      national average) and the Decomposition View already visible.
- [x] The decomposition shows by default for the Sector on the map; clicking a
      radar axis or the in-drawer selector switches the decomposed Sector.
- [x] Dimension and Indicator scores are shown with each Indicator's reference
      year, data source, and a completeness flag where the score is incomplete.
- [x] Environment's dimension-less path renders correctly (Indicators directly
      under the Sector Index, no Supply/Access rows).
- [x] Mostly-urban Districts show the Urban note; the Agriculture land-use
      explanation is surfaced in that context.
- [x] Closing the drawer returns to the scan with the previous selection intact.

## Comments

Ported the prototype's drawer onto the production layout's "declare components
up front" philosophy (rather than the prototype's build-inline approach) — the
drawer's radar, decomposed-Sector `Select`, decomposition container, and
Urban-chip container are declared in `layout.py`; callbacks only set their
`children`/`figure`/`value`.

- `layout.py` — a right `dmc.Drawer(id="detail-drawer")` sibling of the AppShell,
  holding the Urban-chip container, the radar `Graph`, a `Divider`, the
  `drawer-sector` Select (all Sectors), and the `decomp-content` container.
- `callbacks.py` —
  - `_open_district_drawer` (Input `selected-district`, State `sector-select`):
    opens the drawer, sets the title (`<name> · <province>`), the Urban chip, the
    radar, and `drawer-sector.value` = the map's Sector. Setting that value drives
    `_render_decomposition`, so the Decomposition View shows with **no second
    click** (the ticket's key v1 fix).
  - `_axis_to_decomposed_sector` (Input `radar.clickData`) and the in-drawer
    Select both write `drawer-sector.value` (the axis path via `allow_duplicate`).
  - `_render_decomposition` (Inputs `drawer-sector.value` **and**
    `selected-district`) re-renders the breakdown on either a Sector switch or a
    new District (so a new District with an unchanged Sector still refreshes).
  - `compute_decomposition_children` rewritten from `dash_table.DataTable` to DMC
    cards (the prototype's score-level style; raw figures + compare chart are
    ticket 07): a Dimension-scores section (omitted for Environment, ADR-0003)
    and per-Indicator cards showing the humanised label, Dimension badge,
    reference year · data source, and the 0-100 score.
  - The Urban land-use `Alert` is gated on `is_urban and sector == Agriculture`,
    so it is contextual (spec.md), while the always-in-drawer Urban chip marks the
    District regardless of Sector.
- `app.py` / `register_callbacks` — threaded `SECTORS` through for the radar axis
  order and the axis-click Sector validation.

Tests: DMC-card decomposition (dimension + indicator sections, ref-year/source,
Environment no-Dimension path, incomplete-Dimension flag), the contextual Urban
note, and `_district_title`. Added indicator metadata to the app-test fixture so
reference year/source render. Full suite: 164 passed.

`/code-review` (Standards + Spec) — acted on the findings that mattered:
- **Fixed (Spec)** — the completeness flag lived only on Dimension rows, so a
  dimension-less Environment Sector Index surfaced **no** completeness signal — a
  dark-but-incomplete District would read as confident (the exact misread spec.md
  warns against). `read_district_decomposition` now also returns the Sector Index
  row; `shape_decomposition` exposes `sector_complete`; the drawer shows a
  Sector-level "Incomplete data" alert when the Sector Index used incomplete
  Indicators — covering Environment and every Sector. (Per-Indicator flags aren't
  meaningful: the read drops absent Indicators, so a present Indicator always has
  a score.)
- **Fixed (Standards)** — reworded the `layout.py` comment: the Urban *chip* is
  built in the callback; only its *container* is declared up front.
- **Noted, not changed** — on a fresh selection whose Sector differs from the
  drawer's prior value, the decomposition may render the previous Sector for one
  frame before the value-set re-render corrects it (cosmetic, not an acceptance
  failure).
