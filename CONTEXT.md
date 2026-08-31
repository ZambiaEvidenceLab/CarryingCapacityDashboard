# Carrying Capacity Assessment (CCA)

A district-level methodology for scoring how much government capacity exists, per sector, to sustain the needs of Zambia's population — built as five independent sector indices, not a single national ranking.

## Language

**Sector**:
One of the five top-level areas assessed: Health, Education, Agriculture, Infrastructure, Environment. Each district gets one score per sector (an exception for Environment, see below).
_Avoid_: Pillar, domain (when referring to a Sector specifically)

**Dimension**:
For Health, Education, Agriculture, and Infrastructure, the two lenses a Sector is scored through: Supply and Access. Environment has no Dimensions — it is scored directly from its Indicators.
_Avoid_: Sub-index, category

**Supply**:
The Dimension capturing government resources and services available in a district (e.g. nurse-to-population ratio).

**Access**:
The Dimension capturing how effectively the population can reach or use the Supply that exists (e.g. distance to nearest facility).

**Indicator**:
A single measured variable that feeds into a Dimension (or directly into an Environment Sector Index). Always standardised min-max to a 0–100 scale and oriented so higher = more capacity before use — for a raw measure where higher naturally means *less* capacity (e.g. distance to nearest facility, or a population-pressure measure like population growth rate), the indicator is inverted first. See [[adr-0009]] for the Environment sector's condition-vs-pressure split.

**Outcome Indicator**:
A measure of a result downstream of capacity (e.g. under-15 mortality), as distinct from an Indicator, which measures capacity itself. Outcome Indicators are excluded from Sector Index math — see [[adr-0001]] — and are tracked only as a future candidate for correlation analysis against the index.
_Avoid_: Using "indicator" alone when the outcome/capacity distinction matters

**Sector Index**:
The 0–100 score for one Sector in one district: the equal-weighted average of its Supply and Access Dimension scores (each Dimension itself an equal-weighted average of its Indicators), or for Environment, the equal-weighted average of its Indicators directly. See [[adr-0003]].

**District**:
The unit of analysis — one of Zambia's 116 districts. Every Indicator, Dimension, and Sector Index is computed at this level.

**Snapshot**:
The single "latest" set of Indicator values the dashboard displays. The database stores a dated value per Indicator per District from day one, but v1 surfaces only the most recent snapshot — no historical/trend view yet. Because Indicators update on different cycles, a Snapshot can mix reference years across Indicators within the same Sector Index; each Indicator's own reference year is shown alongside its value wherever displayed. See [[adr-0004]].
_Avoid_: "Time series" or "trend" when describing what the v1 dashboard shows — it doesn't, yet.

**District Master List**:
The authoritative list of Zambia's 116 districts (name, code, province, boundary) used to validate indicator uploads and render the dashboard map. Sourced live from GRID3's ArcGIS FeatureServer rather than a committed local file — see [[adr-0006]]. Treated as a closed cohort for normalisation purposes: districts are only ever added, removed, or updated as a full 116-district refresh, never individually — see [[adr-0007]].

**Decomposition View**:
The dashboard view reached by drilling into one axis of a district's radar chart, showing that Sector Index's underlying Dimension and Indicator scores individually, so a low Sector Index can be traced to the specific Indicators driving it down (e.g. to inform where investment should be prioritised).

**Raw Submission**:
A file recording one batch of indicator values exactly as received, kept in the data lake — interim storage: the private repo and local machine; long-term storage still to be decided — and never overwritten or edited in place. Tracked via a Postgres catalog entry carrying audit metadata (submitter, timestamp, file location) and a status of `pending`, `published`, or `rejected`. Only the validation pipeline can promote a submission to `published` — deriving processed, cleaned data from it, stored in PostgreSQL — or mark it `rejected`; the raw file itself is retained either way. See [[adr-0012]], [[adr-0016]].

**Data completeness**:
A per-District, per-Dimension (or per-Sector, for Environment) flag showing when a score was computed from fewer than the full set of Indicators because one or more was missing for that District. Missing Indicators are dropped and the remainder re-averaged, rather than imputed, for now.
