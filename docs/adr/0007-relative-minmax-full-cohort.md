---
status: accepted
---

# Relative min-max normalisation, recomputed over the full district cohort each refresh

Per the OECD Handbook (Step 5), we normalise indicators via min-max scaled to [0, 100]. We decided the min and max are recomputed from the current 116 districts every time an indicator refreshes — not anchored to fixed, externally-set benchmarks — and that every refresh covers the full 116-district cohort at once; districts are never added, removed, or updated individually outside a full-cohort refresh.

This is a deliberate choice, not the default because it's easiest: fixed benchmarks would require MoFNP to formally agree a target value for every indicator before any score could be computed, which isn't realistic ahead of the workshop. Relative normalisation works as soon as real data lands, at the cost of a real interpretive tradeoff that must be surfaced on the dashboard's methodology page — a district's score can move between refreshes even if its own raw numbers didn't change, because other districts moved. The full-cohort-only constraint is what keeps this well-defined: min-max is only ever computed over one complete, simultaneous set of 116 values, never a partial or straggling one.

**Revisit when**: MoFNP wants scores that are stable and interpretable as "met a defined target" rather than "ranked against peers this cycle" — that would mean introducing fixed benchmarks per indicator (a data-collection exercise in its own right, not just a methodology switch).
