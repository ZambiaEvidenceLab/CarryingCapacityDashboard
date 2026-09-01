"""District-name matching against the GRID3 master list (spec: "Validation and publish pipeline").

Raw submissions arrive with human-readable district names, not GRID3 codes.
This is the first validation step: resolve each name to its `district_code`
so every later step (the 116-district cohort check, scoring) can work in
codes, and reject the submission outright if any name doesn't resolve.
"""

from __future__ import annotations

import pandas as pd

from cca.grid3.client import District
from cca.scoring.engine import ValidationResult


def _normalise(name: str) -> str:
    return " ".join(str(name).split()).casefold()


def match_district_names(
    raw_values: pd.DataFrame,
    districts: list[District],
) -> tuple[pd.DataFrame, ValidationResult]:
    """Resolve `raw_values["district_name"]` to `district_code`, case/whitespace-insensitively.

    Returns the input with `district_name` replaced by `district_code`
    (rows with an unresolvable name are dropped from this output — the
    accompanying `ValidationResult` fails whenever that happens, so callers
    that check `passed` first never rely on the dropped rows) alongside the
    `ValidationResult`.
    """
    code_by_name = {_normalise(d.name): d.code for d in districts}

    resolved = raw_values["district_name"].map(lambda name: code_by_name.get(_normalise(name)))
    unmatched = sorted(set(raw_values.loc[resolved.isna(), "district_name"]))

    reasons = []
    if unmatched:
        reasons.append(f"District names not found in the GRID3 master list: {unmatched}")

    mapped = raw_values.loc[resolved.notna()].copy()
    mapped["district_code"] = resolved.loc[resolved.notna()]
    mapped = mapped.drop(columns=["district_name"]).reset_index(drop=True)

    return mapped, ValidationResult(passed=not reasons, reasons=reasons)
