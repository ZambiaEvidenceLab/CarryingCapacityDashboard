# 04 — Ranked District list, linked to the map

**What to build:** The priority carrier. Fill the right-hand column with a
**ranked list of Districts, worst-served first** for the selected Sector — the
direct answer to "who is most underserved?" for a budget allocator. Each row
shows rank, District name, the Sector Index score with a small inline microbar, a
data-completeness dot, and an "Urban" chip where relevant. Selecting a row — or
clicking the District on the map — selects that District (the shared selection
ticket 06's drawer consumes). Because dark = high capacity means priorities look
*pale* on the map, this list is where the exact ordering lives.

**Blocked by:** 03 (shell + map).

**Status:** ready-for-agent

- [ ] The list renders all scored Districts for the selected Sector, sorted
      ascending by score (worst-served first) by default.
- [ ] Each row shows rank, name, score + microbar, a completeness dot (amber when
      the score used incomplete Indicators), and an "Urban" chip for mostly-urban
      Districts.
- [ ] Clicking a row and clicking a map District both set the same selected
      District; the selection is visible in both (map + list stay in step).
- [ ] Data-completeness is also signalled on the map (e.g. a distinct overlay or
      border for incomplete Districts) so a pale-but-incomplete District is not
      mistaken for a confident low score — note a scatter overlay layer may be
      needed since `Choroplethmap` has no native per-District hatch.
- [ ] Switching Sector re-ranks the list.
- [ ] Domain vocabulary (District, Sector Index, Data completeness) is used in all
      labels.
