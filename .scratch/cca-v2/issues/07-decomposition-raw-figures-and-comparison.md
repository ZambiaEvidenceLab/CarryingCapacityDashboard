# 07 — Decomposition figures: raw values and compare-to-others charts

**What to build:** Turn the decomposition from a table of abstract 0–100 scores
into something a Ministry user can act on. For each Indicator in the Decomposition
View, show the **raw value with its unit** (e.g. "12.3 per 10k") alongside the
normalised score, and a **compare-to-others chart** — the distribution of all 116
Districts on that Indicator's raw value, with *this* District highlighted, the
others greyed, and the **national average** marked. Where a National Development
Plan objective exists for the Indicator, draw it as a line on the same chart (in
raw units). This shows not just how low a District is, but how low relative to its
peers and to any national target.

**Reuse from the prototype** (`.scratch/cca-v2/prototype/app.py`):
`build_compare_fig` (highlighted District, national-mean line, objective line)
and the raw-value part of `decomposition_cards`. Feed them from ticket 02's read
paths (a District's raw values; the cohort's values for one Indicator) instead of
the synthetic `D.indicator_rows` / `D.indicator_distribution`. The prototype used
a jittered strip; a histogram or beeswarm is an acceptable substitute once judged
against real data.

**Blocked by:** 06 (drawer + decomposition), 02 (raw values available to read).

**Status:** ready-for-agent

- [ ] Each Indicator row shows its raw value + unit and its normalised score.
- [ ] Each Indicator shows a compare-to-others chart of all 116 Districts' raw
      values, this District highlighted, others greyed, national average marked.
- [ ] Where a metadata objective/target exists for the Indicator, it is drawn as a
      labelled line in raw units; absent targets simply omit the line.
- [ ] Districts with no value for an Indicator are handled gracefully (no chart /
      clear "no value reported" state), consistent with dropped-not-imputed.
- [ ] All figures come from the processed layer read paths (no runtime
      calculation — ADR-0010).
