# 02 — Persist raw Indicator values and expose them to the dashboard

**What to build:** The data-model change that lets the dashboard show a
Ministry user the **actual figure** behind each Indicator (e.g. "12.3 per 10k"),
not only its 0–100 normalised score, and lets a raw-unit National Development
Plan objective be drawn against it. Today the processed layer stores only the
normalised value, and ADR-0016 states raw values never live there. This ticket
persists the numeric raw value per Indicator per District per run alongside the
normalised one, and exposes it to the read-only dashboard — both a single
District's raw values and the whole cohort's values for one Indicator (needed by
the compare-to-others chart in ticket 07).

This **revisits ADR-0016**: write a new ADR that distinguishes the raw
*submission files* (which still never enter the processed layer) from the numeric
raw *value* the dashboard needs. No scoring methodology changes — winsorize /
min-max / aggregation are untouched; the raw value is merely also stored.

**Blocked by:** None — can start immediately (parallel to the UI chain).

**Status:** ready-for-agent

- [ ] A new ADR (amending/superseding ADR-0016) records the decision and its
      boundary: raw numeric values are stored in the processed layer for display;
      raw submission files are not.
- [ ] The processed `indicators` layer stores the raw value beside the normalised
      value per District per Indicator per run (append-only per ADR-0014; missing
      Indicators still simply have no row).
- [ ] The scoring/pipeline run writes both values in one pass (the raw value is
      already in hand when normalising).
- [ ] An optional per-Indicator objective/target field exists in the metadata
      catalog (nullable — holds a future NDP target; empty until MoFNP supplies).
- [ ] Read paths expose (a) one District's raw + normalised Indicator values and
      (b) all 116 Districts' raw values for a single Indicator, read-only.
- [ ] A light integration test confirms both read shapes return correct values
      from a seeded run (per the spec's testing decision — no scoring-engine
      coverage duplicated at the adapter boundary).
