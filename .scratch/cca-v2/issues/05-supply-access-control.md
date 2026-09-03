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

**Blocked by:** 03 (map), 04 (list).

**Status:** ready-for-agent

- [ ] The `Overall · Supply · Access` control recolours the map and re-ranks the
      list to the selected Dimension.
- [ ] The map recolour uses a partial (`Patch`) update — the geometry is not
      re-sent when only the measure changes (verify no full-figure resend).
- [ ] Selecting Environment hides/disables the control and shows only Overall.
- [ ] A hover beside the control lists the current Sector's Supply and Access
      Indicators (and notes Environment's no-split case).
- [ ] The subtitle reflects the selected Dimension.
