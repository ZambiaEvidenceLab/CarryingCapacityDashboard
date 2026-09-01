"""Pure scoring engine for the Carrying Capacity Assessment.

Accepts and returns plain pandas/dataclass data. No database, file I/O, or
network calls — see ADR-0007, ADR-0008, ADR-0009, ADR-0003, ADR-0001.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

VALID_ORIENTATIONS = {"normal", "invert"}


@dataclass(frozen=True)
class IndicatorMeta:
    indicator_id: str
    sector: str
    dimension: str | None  # "Supply", "Access", or None for Environment
    orientation: str = "normal"  # "normal" or "invert" (ADR-0009)

    def __post_init__(self) -> None:
        if self.orientation not in VALID_ORIENTATIONS:
            raise ValueError(
                f"Unknown orientation {self.orientation!r} for {self.indicator_id}"
            )


@dataclass
class ValidationResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class WinsorizationReport:
    indicator_id: str
    lower_bound: float
    upper_bound: float
    capped_districts: list[str]
    pre: dict[str, float]
    post: dict[str, float]


@dataclass
class IndicatorScore:
    indicator_id: str
    normalised: pd.Series  # district_code -> value in [0, 100], or NaN if missing
    winsorization: WinsorizationReport


@dataclass
class AggregateScore:
    value: float | None
    complete: bool
    n_indicators_used: int
    n_indicators_total: int


@dataclass
class ScoringResult:
    validation: ValidationResult
    winsorization_reports: dict[str, WinsorizationReport]
    indicator_scores: dict[str, IndicatorScore]
    dimension_scores: pd.DataFrame
    sector_scores: pd.DataFrame


def validate_full_cohort(
    raw_values: pd.DataFrame,
    district_master_list: list[str],
    *,
    allow_partial: bool = False,
) -> ValidationResult:
    """Reject submissions that don't cover the full district cohort (ADR-0007).

    Missing *values* for individual indicators are handled separately via
    data-completeness flagging in aggregation — this only checks that every
    master-list district appears somewhere in the submission.
    """
    reasons = []
    submitted = set(raw_values["district_code"].unique())
    master = set(district_master_list)

    unknown = submitted - master
    if unknown:
        reasons.append(f"Unknown districts not in master list: {sorted(unknown)}")

    missing = master - submitted
    if missing and not allow_partial:
        reasons.append(
            f"Missing districts (submission covers {len(submitted & master)}/"
            f"{len(master)}): {sorted(missing)}"
        )

    duplicate_keys = raw_values.duplicated(subset=["district_code", "indicator_id"])
    if duplicate_keys.any():
        duplicates = raw_values.loc[duplicate_keys, ["district_code", "indicator_id"]]
        pairs = sorted(set(map(tuple, duplicates.to_numpy().tolist())))
        reasons.append(f"Duplicate (district, indicator) rows in submission: {pairs}")

    return ValidationResult(passed=not reasons, reasons=reasons)


def _distribution_stats(values: pd.Series) -> dict[str, float]:
    clean = values.dropna()
    if clean.empty:
        return {"min": float("nan"), "max": float("nan"), "mean": float("nan"),
                "std": float("nan"), "skew": float("nan")}
    return {
        "min": float(clean.min()),
        "max": float(clean.max()),
        "mean": float(clean.mean()),
        "std": float(clean.std()),
        "skew": float(clean.skew()),
    }


def winsorize(
    indicator_id: str,
    values: pd.Series,
    *,
    lower_pct: float = 1.0,
    upper_pct: float = 99.0,
) -> tuple[pd.Series, WinsorizationReport]:
    """Cap raw values at the given percentiles before normalisation (ADR-0008)."""
    pre = _distribution_stats(values)
    clean = values.dropna()

    if clean.empty:
        report = WinsorizationReport(indicator_id, float("nan"), float("nan"), [], pre, pre)
        return values.copy(), report

    lower_bound = float(np.percentile(clean, lower_pct))
    upper_bound = float(np.percentile(clean, upper_pct))

    capped = values.clip(lower=lower_bound, upper=upper_bound)
    capped_mask = ((values < lower_bound) | (values > upper_bound)).fillna(False)
    capped_districts = capped_mask[capped_mask].index.tolist()

    post = _distribution_stats(capped)
    report = WinsorizationReport(indicator_id, lower_bound, upper_bound, capped_districts, pre, post)
    return capped, report


def orient(values: pd.Series, orientation: str) -> pd.Series:
    """Invert pressure indicators so higher always means more capacity (ADR-0009)."""
    if orientation == "invert":
        return -values
    return values


def normalise(values: pd.Series) -> pd.Series:
    """Min-max scale to [0, 100] over whatever cohort is passed in (ADR-0007)."""
    clean = values.dropna()
    if clean.empty:
        return values.copy()

    vmin, vmax = clean.min(), clean.max()
    if vmax == vmin:
        return values.where(values.isna(), 100.0)

    return (values - vmin) / (vmax - vmin) * 100.0


def score_indicators(
    raw_values: pd.DataFrame,
    indicator_meta: dict[str, IndicatorMeta],
    district_master_list: list[str],
) -> dict[str, IndicatorScore]:
    """Run winsorize -> orient -> normalise for each indicator, over the full cohort."""
    results: dict[str, IndicatorScore] = {}
    for indicator_id, meta in indicator_meta.items():
        subset = (
            raw_values[raw_values["indicator_id"] == indicator_id]
            .set_index("district_code")["value"]
            .reindex(district_master_list)
        )
        winsorized, report = winsorize(indicator_id, subset)
        oriented = orient(winsorized, meta.orientation)
        normalised = normalise(oriented)
        results[indicator_id] = IndicatorScore(indicator_id, normalised, report)
    return results


def aggregate(
    indicator_ids: list[str],
    indicator_scores: dict[str, IndicatorScore],
    district_code: str,
) -> AggregateScore:
    """Average present indicator scores for a district; missing ones are dropped, not imputed."""
    total = len(indicator_ids)
    present = [
        v
        for v in (indicator_scores[i].normalised.get(district_code) for i in indicator_ids)
        if pd.notna(v)
    ]
    used = len(present)
    if used == 0:
        return AggregateScore(None, complete=False, n_indicators_used=0, n_indicators_total=total)
    return AggregateScore(
        value=float(np.mean(present)),
        complete=(used == total),
        n_indicators_used=used,
        n_indicators_total=total,
    )


def run_scoring(
    raw_values: pd.DataFrame,
    indicator_metas: list[IndicatorMeta],
    district_master_list: list[str],
    *,
    allow_partial_cohort: bool = False,
) -> ScoringResult:
    """Full pipeline: validate cohort, score indicators, aggregate to Dimension and Sector."""
    validation = validate_full_cohort(raw_values, district_master_list, allow_partial=allow_partial_cohort)
    if not validation.passed:
        return ScoringResult(validation, {}, {}, pd.DataFrame(), pd.DataFrame())

    meta_by_id = {m.indicator_id: m for m in indicator_metas}
    indicator_scores = score_indicators(raw_values, meta_by_id, district_master_list)
    winsorization_reports = {iid: s.winsorization for iid, s in indicator_scores.items()}

    # sector -> dimension (None for Environment) -> [indicator_id, ...]
    sectors: dict[str, dict[str | None, list[str]]] = {}
    for m in indicator_metas:
        sectors.setdefault(m.sector, {}).setdefault(m.dimension, []).append(m.indicator_id)

    dimension_rows = []
    sector_rows = []
    for district_code in district_master_list:
        for sector, dims in sectors.items():
            if set(dims.keys()) == {None}:
                # Environment's dimension-less path: indicators average directly (ADR-0003).
                agg = aggregate(dims[None], indicator_scores, district_code)
                sector_rows.append(_score_row(district_code, sector, agg))
                continue

            dim_aggs = {
                dimension: aggregate(ids, indicator_scores, district_code)
                for dimension, ids in dims.items()
            }
            for dimension, agg in dim_aggs.items():
                dimension_rows.append(_score_row(district_code, sector, agg, dimension=dimension))

            dim_values = [a.value for a in dim_aggs.values() if a.value is not None]
            sector_value = float(np.mean(dim_values)) if dim_values else None
            sector_agg = AggregateScore(
                value=sector_value,
                complete=all(a.complete for a in dim_aggs.values()),
                n_indicators_used=sum(a.n_indicators_used for a in dim_aggs.values()),
                n_indicators_total=sum(a.n_indicators_total for a in dim_aggs.values()),
            )
            sector_rows.append(_score_row(district_code, sector, sector_agg))

    dimension_columns = ["district_code", "sector", "dimension", "score", "complete", "n_used", "n_total"]
    sector_columns = ["district_code", "sector", "score", "complete", "n_used", "n_total"]
    return ScoringResult(
        validation,
        winsorization_reports,
        indicator_scores,
        pd.DataFrame(dimension_rows, columns=dimension_columns),
        pd.DataFrame(sector_rows, columns=sector_columns),
    )


def _score_row(district_code: str, sector: str, agg: AggregateScore, *, dimension: str | None = None) -> dict:
    row = {
        "district_code": district_code,
        "sector": sector,
        "score": agg.value,
        "complete": agg.complete,
        "n_used": agg.n_indicators_used,
        "n_total": agg.n_indicators_total,
    }
    if dimension is not None:
        row["dimension"] = dimension
    return row


def decomposition_view(
    sector: str,
    district_code: str,
    indicator_metas: list[IndicatorMeta],
    indicator_scores: dict[str, IndicatorScore],
) -> dict[str, dict]:
    """Trace a Sector Index down to its Dimension and Indicator scores for one district."""
    relevant = [m for m in indicator_metas if m.sector == sector]

    dims: dict[str | None, list[IndicatorMeta]] = {}
    for m in relevant:
        dims.setdefault(m.dimension, []).append(m)

    breakdown = {}
    for dimension, metas in dims.items():
        indicator_ids = [m.indicator_id for m in metas]
        agg = aggregate(indicator_ids, indicator_scores, district_code)
        indicators = []
        for m in metas:
            score = indicator_scores[m.indicator_id].normalised.get(district_code)
            indicators.append({
                "indicator_id": m.indicator_id,
                "value": None if pd.isna(score) else float(score),
                "missing": bool(pd.isna(score)),
            })
        key = dimension if dimension is not None else sector
        breakdown[key] = {
            "score": agg.value,
            "complete": agg.complete,
            "indicators": indicators,
        }
    return breakdown
