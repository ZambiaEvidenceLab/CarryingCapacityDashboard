"""Synthetic indicator-value generator for the CCA pipeline.

Produces plausible fake raw indicator values across the full district
cohort so the scoring engine, data pipeline, and dashboard can be built and
demoed before real MoFNP data arrives (spec: "Synthetic data generator").
Deliberately includes missing values (to exercise data-completeness
flagging) and outliers (to exercise winsorization) rather than only the
happy path.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from cca.grid3.client import District
from cca.scoring.engine import IndicatorMeta
from cca.scoring.indicators import CCA_INDICATORS

DEFAULT_MISSING_RATE = 0.05
DEFAULT_OUTLIER_RATE = 0.02


@dataclass(frozen=True)
class IndicatorRange:
    """Plausible raw-value range for one Indicator, used to seed synthetic data.

    A rough guess for generating realistic-*looking* synthetic data — not a
    source of truth for real indicator values.
    """

    low: float
    high: float


# Rough plausible raw-value ranges per Indicator (see CCA_indicator_list.csv
# for the unit each one is expressed in).
INDICATOR_RANGES: dict[str, IndicatorRange] = {
    "health_doctor_to_population_ratio": IndicatorRange(0.01, 0.5),
    "health_nurse_to_population_ratio": IndicatorRange(0.1, 3.0),
    "health_facilities_with_functional_emonc": IndicatorRange(0, 20),
    "health_skilled_birth_attendance_rate": IndicatorRange(20, 100),
    "health_distance_to_nearest_facility": IndicatorRange(1, 60),
    "health_pct_population_registered_nhima": IndicatorRange(0, 80),
    "education_pupil_teacher_ratio_primary": IndicatorRange(20, 90),
    "education_pupil_teacher_ratio_secondary": IndicatorRange(15, 70),
    "education_electrification_of_schools": IndicatorRange(0, 100),
    "education_schools_with_internet": IndicatorRange(0, 100),
    "education_distance_to_nearest_school": IndicatorRange(0.5, 25),
    "education_mean_years_of_schooling": IndicatorRange(2, 12),
    "agriculture_extension_worker_to_farmer_ratio": IndicatorRange(200, 1500),
    "agriculture_maize_production_per_capita": IndicatorRange(0, 5),
    "agriculture_fra_storage_tonnes_per_capita": IndicatorRange(0, 2),
    "agriculture_pct_population_receiving_fisp": IndicatorRange(0, 60),
    "agriculture_pct_farmers_reached_by_extension": IndicatorRange(0, 80),
    "infrastructure_water_point_density": IndicatorRange(0, 10),
    "infrastructure_grid_connection_capacity": IndicatorRange(0, 100),
    "infrastructure_network_tower_coverage": IndicatorRange(0, 100),
    "infrastructure_pct_households_safe_water": IndicatorRange(10, 100),
    "infrastructure_distance_to_nearest_water_point": IndicatorRange(0.1, 15),
    "infrastructure_pct_households_electrified": IndicatorRange(0, 100),
    "environment_forest_cover": IndicatorRange(5, 90),
    "environment_ecological_diversity": IndicatorRange(0, 100),
    "environment_population_growth_rate": IndicatorRange(-1, 6),
    "environment_cattlehead_per_capita": IndicatorRange(0, 3),
    "environment_charcoal_consumption_domestic": IndicatorRange(0, 500),
}


def generate_synthetic_indicators(
    district_codes: list[str],
    indicator_metas: list[IndicatorMeta],
    *,
    seed: int | None = None,
    missing_rate: float = DEFAULT_MISSING_RATE,
    outlier_rate: float = DEFAULT_OUTLIER_RATE,
) -> pd.DataFrame:
    """Generate a plausible fake raw-indicator table for the full cohort.

    Output columns (`district_code`, `indicator_id`, `value`) match the
    scoring engine's expected input format, so the result can be fed
    straight into `run_scoring`.

    `missing_rate` and `outlier_rate` are fractions of all (district,
    indicator) cells; a `rate > 0` always yields at least one occurrence
    regardless of cohort size, so completeness flagging and winsorization
    both get exercised even on a small fixture.
    """
    rng = np.random.default_rng(seed)

    unknown = sorted({m.indicator_id for m in indicator_metas} - INDICATOR_RANGES.keys())
    if unknown:
        raise ValueError(f"No synthetic value range defined for indicators: {unknown}")

    rows = []
    for meta in indicator_metas:
        value_range = INDICATOR_RANGES[meta.indicator_id]
        values = rng.uniform(value_range.low, value_range.high, size=len(district_codes))
        rows.extend(
            {"district_code": district_code, "indicator_id": meta.indicator_id, "value": float(value)}
            for district_code, value in zip(district_codes, values)
        )

    n_total = len(rows)
    n_missing = _cell_count(n_total, missing_rate)
    n_outlier = _cell_count(n_total, outlier_rate)
    shuffled_indices = rng.permutation(n_total)
    missing_indices = set(shuffled_indices[:n_missing].tolist())
    outlier_indices = shuffled_indices[n_missing : n_missing + n_outlier]

    for idx in outlier_indices:
        rows[idx]["value"] = _push_outlier(rows[idx]["value"], INDICATOR_RANGES[rows[idx]["indicator_id"]], rng)

    kept_rows = [row for i, row in enumerate(rows) if i not in missing_indices]
    return pd.DataFrame(kept_rows, columns=["district_code", "indicator_id", "value"])


def generate_synthetic_dataset(
    districts: list[District],
    *,
    indicator_metas: list[IndicatorMeta] | None = None,
    seed: int | None = None,
    missing_rate: float = DEFAULT_MISSING_RATE,
    outlier_rate: float = DEFAULT_OUTLIER_RATE,
) -> pd.DataFrame:
    """Convenience wrapper over the real GRID3 district master list and the canonical CCA indicator catalog."""
    district_codes = [district.code for district in districts]
    return generate_synthetic_indicators(
        district_codes,
        indicator_metas if indicator_metas is not None else CCA_INDICATORS,
        seed=seed,
        missing_rate=missing_rate,
        outlier_rate=outlier_rate,
    )


def _cell_count(n_total: int, rate: float) -> int:
    if rate <= 0:
        return 0
    return max(1, round(n_total * rate))


def _push_outlier(value: float, value_range: IndicatorRange, rng: np.random.Generator) -> float:
    """Push a value well past the indicator's normal span so it survives 1st/99th-percentile winsorization."""
    span = value_range.high - value_range.low or 1.0
    direction = rng.choice([-1.0, 1.0])
    magnitude = rng.uniform(3.0, 6.0) * span
    return value + direction * magnitude
