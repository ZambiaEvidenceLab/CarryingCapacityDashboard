# 05 — Supply/Access segmented control and hover legend

**What to build:** Make the Supply-gap vs Access-gap distinction actionable at
the prioritisation step, not buried in a drill-down. Add an `Overall · Supply ·
Access` segmented control above the map. Switching it **recolours the map and
re-ranks the list** to the chosen Dimension, reframing "underserved" in one
click. The map recolour goes through `Patch()` — only the score array and range
change, the boundary geometry is never re-sent (ADR-0017, lever 3). Environment
has no Dimensions (ADR-0003), so the control is hidden/disabled for it — only
Overall applies. A small **"what's in Supply / Access?" hover** beside the
control lists the current Sector's Supply and Access Indicators, so a user can
see what each Dimension contains without opening a District.

**Reuse from the prototype** (`.scratch/cca-v2/prototype/app.py`): the measure
`Patch()` branch in `_view`, `_measure_availability` (Environment → Overall
only), and `sa_legend_content` (the Supply/Access hover contents).

**Blocked by:** 03 (map), 04 (list).

**Status:** done

- [x] The `Overall · Supply · Access` control recolours the map and re-ranks the
      list to the selected Dimension.
- [x] The map recolour uses a partial (`Patch`) update — the geometry is not
      re-sent when only the measure changes (verify no full-figure resend).
- [x] Selecting Environment hides/disables the control and shows only Overall.
- [x] A hover beside the control lists the current Sector's Supply and Access
      Indicators (and notes Environment's no-split case).
- [x] The subtitle reflects the selected Dimension.

## Comments

Ported the prototype's Measure control onto the ticket-04 pure-seam / callback
split. A **Measure** is `Overall` (the Sector Index) or a named Dimension
(`Supply`/`Access`) — the Dimension values double as the `indices.scores.dimension`
value read back, so the domain term carries straight from the DB to the label.

- `storage/io.py` — `read_latest_dimension_scores(engine, sector, dimension)`
  returns the Supply/Access rows (`dimension = :dimension`) in the same shape as
  `read_latest_sector_scores` (the Sector Index, `dimension IS NULL`), so the
  map/list recolour and re-rank with no re-derivation (ADR-0010).
- `dashboard/data.py` — pure measure helpers: `MEASURES`/`OVERALL_ONLY`,
  `SECTORS_WITH_DIMENSIONS` (derived from the catalog, not hard-coded to
  Environment), `effective_measure` (collapses a Dimension to Overall for a
  dimension-less Sector, guarding the data path independently of the control),
  `indicator_label`, and `sector_dimension_indicators` (the hover's grouped
  Indicator labels).
- `dashboard/callbacks.py` — `compute_map_measure_patch` recolours via `Patch()`:
  only trace 0's `z`/`zmin`/`zmax`/`colorbar` and the amber completeness overlay
  (trace 2) change; the `geojson` is never re-attached and the selection halo
  (trace 1) is untouched (ADR-0017 lever 3). `compute_map_figure`/
  `compute_ranked_list`/`compute_subtitle` gained a `measure` arg;
  `compute_supply_access_legend` builds the hover; `_configure_measure_control`
  swaps the control to Overall-only **and disables it** for Environment.
- `dashboard/layout.py` — the `Overall · Supply · Access` `SegmentedControl` plus
  a `HoverCard` ("ⓘ what's in Supply / Access?") beside the Sector select.

Deliberate deviation from the prototype's z-only Patch: the completeness overlay
is recomputed **per Measure** (not just per Sector), because a District complete
Overall can be incomplete on one Dimension — the amber dot must track the shown
score. Guarded by `test_completeness_overlay_tracks_the_displayed_measure`.

Tests: pure coverage for the measure helpers (`test_dashboard_data.py`) and
integration for the recolour/re-rank, the Patch-not-resend contract, the
completeness-tracks-measure deviation, the Environment→Overall collapse, the
Measure subtitle, and the hover legend (`test_dashboard_app.py`). Full suite:
153 passed.

`/code-review` (Standards + Spec) — acted on the two findings that mattered:
- **Fixed (Spec)** — Environment showed an Overall-only but still-*enabled*
  control; the ticket asks to "hide/disable". Added a `disabled` output so the
  control is disabled (and Overall-only) for the dimension-less Sector.
- **Fixed (Standards)** — renamed `sa_legend_content` →
  `compute_supply_access_legend` to match the module's `compute_*` public-builder
  convention and expand the "sa" abbreviation.
- **Noted, not changed** — the "Measure"/"Overall" UI vocabulary isn't in
  `CONTEXT.md`'s glossary (Dimension/Sector Index are). Worth a `/domain-modeling`
  pass to add "Measure" (the Overall/Supply/Access selector) and "Overall"
  (= Sector Index) rather than leaving them coined only in code.
