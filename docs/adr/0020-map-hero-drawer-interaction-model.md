---
status: accepted
---

# Map-hero + right-side Drawer as the dashboard's interaction model

v1 stacked everything on one page: map, then a `district-section` that only
appeared after a district click, then a `decomposition-section` below that,
then the full Methodology FAQ at the page bottom — a scroll-down-forever
model (click district -> scroll -> click radar axis -> scroll) that worked
but wasn't quick or decision-grade for a Ministry user scanning 116
districts under budget pressure. v2 replaces it with **map-hero + drawer**,
chosen over a list-hero layout and a KPI-band header in the prototype
(`.scratch/cca-v2/prototype/app.py`) grilling pass:

- **One screen, no scroll, for the national scan.** A `dash-mantine-components`
  `AppShell` puts the map on the left (~60-65%) and a ranked district list on
  the right (~35-40%, ticket 04), replacing v1's stacked sections. The two
  stay **linked** — selecting a district highlights it in both — so the map
  answers "are the priorities geographically clustered?" while the ranked
  list carries the actual priority ordering.
- **Per-district detail lives in a right-side `Drawer`** (ticket 06) that
  slides in over the scan rather than pushing the page down. Closing it
  returns the user to the scan with their place intact — the scan is never
  torn down to show one district's detail, unlike v1's `district-section`/
  `decomposition-section` which replaced the map's visual context with a
  blank map-less block.
- **General Methodology moves behind a header link** (ticket 08) instead of
  living at the page bottom; per-indicator detail moves into the Drawer's
  Decomposition View instead of one long FAQ table. Both surface only when
  asked for, rather than always occupying page real estate below the fold.

This ticket (03) lays the shell and the map only — the Sector control, the
`AppShellHeader` (title, dynamic subtitle, Methodology link), and the map
itself on `go.Choroplethmap` (ADR-0017 lever 2: WebGL, no basemap, per-Sector
hue, live-range shading). Lever 3 (`Patch()`-based recolour with no figure
rebuild) isn't in scope yet: a Sector change still rebuilds the whole figure,
which is correct here since a new Sector means a new colourscale (a new
trace object either way) — lever 3 lands with ticket 05, where the
Supply/Access control repaints only the `z` array and colourbar on the
*same* trace without a Sector change. It deliberately tears out v1's
`district-section`/`decomposition-section`/inline-FAQ components rather
than leaving them dangling against a shell that no longer has a `Drawer` to
put them in; `cca.dashboard.callbacks.compute_radar_figure` and
`compute_decomposition_children` are kept as-is (still directly unit-tested)
for ticket 06 to re-wire once the `Drawer` exists. `compute_summary_strip` is
similarly kept but currently unwired — the old summary strip's job is taken
over by the subtitle and (ticket 04) the ranked list's own per-row
completeness dots, so it may end up unused rather than reinstated; that's a
call for whoever picks up ticket 04/08 to make, not this ticket. The
right-hand column is a placeholder pending ticket 04.

Trade-off accepted: for the span of tickets 03-08, the running dashboard is
visibly incomplete (no ranked list yet, no drawer, no Methodology content) —
acceptable because each ticket is `Blocked by: 03` and lands in sequence, and
building the whole interaction model in one ticket would make it much harder
to review and to bisect if something regresses. Reversible in principle
(nothing here is data-model or storage-layer), but the layout/drawer split is
enough of a structural commitment, and surprising enough to a future reader
("why did the FAQ and radar chart disappear from the page?"), to record here.
