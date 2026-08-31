---
status: accepted
---

# Winsorize extreme values before min-max normalisation, with an automated per-refresh distribution check

The OECD Handbook flags min-max explicitly: "extreme values/outliers could distort the transformed indicator" — a single district with an extreme raw value (e.g. a sparsely populated district producing a huge doctor-to-population ratio off a tiny denominator) stretches the [min, max] range so far that every other district's normalised score compresses into a narrow band, even though their real differences are meaningful.

We decided to cap (winsorize) each indicator's raw values to its 1st/99th percentile *before* applying min-max, rather than using the raw min/max directly. This is a deliberate deviation from plain min-max as described in the README/OECD summary — worth recording so a future engineer doesn't "simplify" it back to raw min-max, not realizing why the cap is there.

**Automated check, run at every refresh** (not a one-off): for each indicator, compute and log the distribution (min, max, mean, std, skew) both before and after winsorization, and record which districts (if any) were capped. This makes the winsorization step transparent rather than a silent transformation, per the OECD's own "documented and explained" requirement for normalisation choices — and gives an early signal if an indicator's data quality is degrading (e.g. a growing number of districts being capped each cycle warrants investigating the source data, not just accepting the cap).

**Revisit when**: real data is available and this can be checked empirically per indicator — some indicators may have no meaningful outliers and the cap will simply never trigger; others may need a different percentile threshold.
