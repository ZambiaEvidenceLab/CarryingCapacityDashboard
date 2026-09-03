---
status: accepted
---

# Raw Indicator values are stored in the processed layer for display; raw submission files still don't live there

[ADR-0016](0016-raw-data-lake-interim-storage.md) says "raw values never live in
PostgreSQL." That statement conflated two different things under one word,
"raw": the **submission file** a Ministry sector submits (a whole CSV/XLSX of
every Indicator, every district, exactly as received) and the **numeric raw
value** behind one Indicator for one district (e.g. `12.3`, the doctor-to-
population ratio before it's normalised to a 0-100 score). ADR-0016's actual
concern — an immutable, auditable record of what was submitted, physically
separate from the queryable processed layer — is about the *file*. It was
never a reason to withhold the *value* the file contains from the one place
that already exists to serve derived, queryable data to the dashboard.

The v2 dashboard's Decomposition View needs the Ministry user's actual figure
("12.3 per 10k"), not only its normalised score, plus a raw-unit National
Development Plan objective line drawn against the cohort's raw values
(`.scratch/cca-v2/spec.md`, "Decomposition figures"). Neither is derivable
from the normalised 0-100 score alone — normalisation is lossy (it depends on
the live cohort min/max) and orientation-flipping (ADR-0009) can even reverse
a value's sign. Recomputing the raw figure from the score is not possible;
the raw value has to be persisted somewhere the dashboard can read from
without runtime calculation (ADR-0010).

**Decision:** `indicators.indicator_values` (schema.py) gains a `raw_value`
column beside the existing normalised `value` column, written in the same
pipeline pass that already holds the raw value in hand before winsorizing/
orienting/normalising it (`score_indicators`, ADR-0008/ADR-0009). The stored
`raw_value` is the value as submitted — before winsorization caps it for
scoring purposes — so it reflects the actual measured figure, not a value
adjusted for outlier-robustness. `metadata.indicator_definitions` gains a
nullable `objective` column for a future NDP per-Indicator target in raw
units, upserted like the rest of the catalog (empty until MoFNP supplies
values).

**Raw submission files remain exactly where ADR-0016 put them** — the data
lake (interim: private repo / local machine), tracked only via the
`catalog.submissions` manifest. This ADR does not reopen that. What changes
is narrower: the processed layer now also stores the numeric value each file
carried, per Indicator per District per run, alongside its normalised score.

**Consequence:** the processed layer's per-row footprint grows by one float
column; this doesn't change ADR-0014's append-only-per-run growth profile or
its "acceptable at this data volume" judgement. No scoring methodology
changes — winsorize, min-max, and aggregation are computed exactly as before
and only the winsorized/oriented/normalised value continues to feed them;
`raw_value` is stored purely for display and objective comparison, and reads
of it must never be fed back into scoring math.
