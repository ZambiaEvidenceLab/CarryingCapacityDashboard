# 04 — Ranked District list, linked to the map

**What to build:** The priority carrier. Fill the right-hand column with a
**ranked list of Districts, worst-served first** for the selected Sector — the
direct answer to "who is most underserved?" for a budget allocator. Each row
shows rank, District name, the Sector Index score with a small inline microbar, a
data-completeness dot, and an "Urban" chip where relevant. Selecting a row — or
clicking the District on the map — selects that District (the shared selection
ticket 06's drawer consumes). Because dark = high capacity means priorities look
*pale* on the map, this list is where the exact ordering lives.

**Reuse from the prototype** (`.scratch/cca-v2/prototype/app.py`): `ranked_rows`,
`completeness_dot`, the `.rank-row` CSS, and the row-id pattern
`{"type": "row", "code": …}` with its selection callback. Replace the synthetic
score lookups with the processed-layer read; keep the structure.

**Blocked by:** 03 (shell + map).

**Status:** done

- [x] The list renders all scored Districts for the selected Sector, sorted
      ascending by score (worst-served first) by default.
- [x] Each row shows rank, name, score + microbar, a completeness dot (amber when
      the score used incomplete Indicators), and an "Urban" chip for mostly-urban
      Districts.
- [x] Clicking a row and clicking a map District both set the same selected
      District; the selection is visible in both (map + list stay in step).
- [x] Data-completeness is also signalled on the map (e.g. a distinct overlay or
      border for incomplete Districts) so a pale-but-incomplete District is not
      mistaken for a confident low score — note a scatter overlay layer may be
      needed since `Choroplethmap` has no native per-District hatch.
- [x] Switching Sector re-ranks the list.
- [x] Domain vocabulary (District, Sector Index, Data completeness) is used in all
      labels.

## Comments

Implemented across the dashboard's existing pure-seam / callback split:

- `data.py` — `shape_ranked_list(sector_scores, districts)` inner-joins the
  Sector's scores to the master list and returns rank/name/score/complete/urban
  rows sorted ascending (worst-served rank 1); `build_district_points(districts)`
  gives one `representative_point()` per District for the map overlays (computed
  once at app startup on the already-simplified boundaries, not per page load).
- `colors.py` — `AMBER` (shared Data-completeness hue) and `SECTOR_DARK` (each
  Sector ramp's dark end, used for the microbar fill and the selection halo).
- `layout.py` — the right column is now the ranked-list Paper (header + scrollable
  `ranked-list` Stack); added `dcc.Store(id="selected-district")` as the shared
  selection ticket 06's Drawer will also read.
- `callbacks.py` — `compute_ranked_list` builds the rows (each a `<button>` with a
  pattern-matching `{"type":"rank-row","code":…}` id). `_select_district` sets the
  shared Store from either a map click or a row click; `_render_ranked_list`
  re-renders on Sector switch (re-rank) or selection change (highlight);
  `_render_map` rebuilds on Sector change only (reads selection from `State`, so a
  selection never resends geometry); `_highlight_map_selection` moves the
  selection halo with `Patch()` (ADR-0017 lever 3). The map gained two `Scattermap`
  overlays `Choroplethmap` can't draw natively: a translucent selection halo and
  amber Data-completeness dots on scored-but-incomplete Districts.
- `app.py` — computes the District points, injects the row CSS, and sets
  `suppress_callback_exceptions=True` (rows are created in a callback, so their
  `n_clicks` Inputs aren't in the startup layout).

Tests: pure-function coverage for `shape_ranked_list` / `build_district_points`
(`test_dashboard_data.py`) and light integration for the ranked list, the re-rank
on Sector switch, the selected-row highlight, and the two map overlays
(`test_dashboard_app.py`). Full suite: 137 passed.

`/code-review` (Standards + Spec) — no hard standards violations. Acted on the
findings that mattered:
- **Fixed (Spec)** — the selection marker was a solid disc drawn *over* the amber
  completeness dot, hiding the incomplete-data signal exactly when a user drilled
  into a selected-but-incomplete District. Now a translucent halo drawn *under*
  the completeness dots (trace order 0 choropleth · 1 selection · 2 completeness).
- **Fixed (Spec)** — clicking the amber dot on a District's centroid selected
  nothing (the overlay point has no `location`). The completeness dots now carry
  the District code in `customdata`, and `_select_district` reads `location` or
  `customdata`, so clicking the marked centre still selects the District.
- **Fixed (Standards)** — dropped two unused trace-index constants and a redundant
  `Patch` marker-colour write (the halo hue can't change on a selection-only path).
- **Noted, not changed** — the map completeness signal is an amber dot, not the
  spec's "hatch/stipple"; the ticket explicitly relaxes this to "a distinct
  overlay … a scatter overlay layer may be needed", and reusing the list's amber
  keeps one completeness meaning across list and map. A true hatch would need a
  raster/pattern layer `Choroplethmap` doesn't offer.
