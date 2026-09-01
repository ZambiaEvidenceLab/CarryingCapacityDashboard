"""Per-indicator range/type constraints for the validation pipeline (spec: "Validation and publish pipeline").

Reuses the same plausible-range table the synthetic data generator seeds
from (`cca.synthetic.generator.INDICATOR_RANGES`) — both describe the same
real-world domain knowledge about each Indicator's unit, just put to
different uses: there it seeds *fake* values, here it's a sanity bound on
*submitted* values. Neither use treats the table as ground truth (MoFNP data
may legitimately widen it later); it's a soft plausibility check, not a hard
scientific limit.
"""

from __future__ import annotations

import math

import pandas as pd

from cca.scoring.engine import ValidationResult
from cca.synthetic.generator import INDICATOR_RANGES


def _is_number(value: object) -> bool:
    try:
        return not math.isnan(float(value)) if not isinstance(value, bool) else False
    except (TypeError, ValueError):
        return False


def check_constraints(
    raw_values: pd.DataFrame, indicator_ids: list[str], *, id_column: str = "district_code"
) -> ValidationResult:
    """Reject rows whose `indicator_id` is unknown, or whose `value` isn't numeric or falls outside range.

    `id_column` names whichever column identifies the row's district in
    reason strings (`district_code` once district-name matching has run,
    `district_name` before it) — this check doesn't care which, since it
    never joins against the district master list itself.

    A missing value (NaN, or simply absent for a district) is not a
    constraint violation — that's the scoring engine's data-completeness
    concern, not this pipeline step's.
    """
    known_ids = set(indicator_ids)
    reasons: list[str] = []

    unknown_indicators = sorted(set(raw_values["indicator_id"]) - known_ids)
    if unknown_indicators:
        reasons.append(f"Indicator ids not in the indicator catalog: {unknown_indicators}")

    for row in raw_values.itertuples(index=False):
        row_id = getattr(row, id_column)
        if row.indicator_id not in known_ids:
            continue
        if pd.isna(row.value):
            continue
        if not _is_number(row.value):
            reasons.append(f"Non-numeric value {row.value!r} for {row.indicator_id} at {row_id}")
            continue

        value_range = INDICATOR_RANGES.get(row.indicator_id)
        if value_range is None:
            continue
        value = float(row.value)
        if not (value_range.low <= value <= value_range.high):
            reasons.append(
                f"Value {value} for {row.indicator_id} at {row_id} is outside "
                f"the plausible range [{value_range.low}, {value_range.high}]"
            )

    return ValidationResult(passed=not reasons, reasons=reasons)
