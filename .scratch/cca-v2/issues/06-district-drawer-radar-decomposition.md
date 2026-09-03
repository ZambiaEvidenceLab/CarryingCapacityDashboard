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

**Blocked by:** 04 (District selection).

**Status:** ready-for-agent

- [ ] Selecting a District opens the right drawer with the radar (District vs
      national average) and the Decomposition View already visible.
- [ ] The decomposition shows by default for the Sector on the map; clicking a
      radar axis or the in-drawer selector switches the decomposed Sector.
- [ ] Dimension and Indicator scores are shown with each Indicator's reference
      year, data source, and a completeness flag where the score is incomplete.
- [ ] Environment's dimension-less path renders correctly (Indicators directly
      under the Sector Index, no Supply/Access rows).
- [ ] Mostly-urban Districts show the Urban note; the Agriculture land-use
      explanation is surfaced in that context.
- [ ] Closing the drawer returns to the scan with the previous selection intact.
