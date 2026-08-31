---
status: accepted
---

# Precompute Sector Index scores; the dashboard app performs no calculation at runtime

The Dash app is effectively static: it only ever reads Sector Index scores (and the per-indicator detail behind them) that were calculated once, during the data-refresh pipeline, and never recomputes anything live. This includes the indicator-level normalised scores, not just the final Sector Index — the refresh pipeline materialises both, since the dashboard's decomposition view (see the Dashboard section of the README) needs to show a district's per-indicator breakdown, not just its aggregate score.

This keeps the running app simple and cheap to host — a real consideration given hosting is still an open workshop question, and a read-only static app is a much smaller ask of whatever infrastructure MoFNP eventually provides than a backend doing live aggregation queries. It also makes the exact score shown to a user on a given date fully auditable — "what was computed at the last refresh," not "what the aggregation query returns right now" — consistent with why [ADR-0007](0007-relative-minmax-full-cohort.md) and [ADR-0008](0008-winsorize-before-minmax.md) already treat each refresh as a discrete, checkable event.
