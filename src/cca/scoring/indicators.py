"""Canonical Indicator catalog for the CCA scoring engine.

Mirrors `CCA_indicator_list.csv` at the repo root. Every Indicator is
oriented so that higher always means more capacity (CONTEXT.md); this file
is the single place that records, per Indicator, whether the raw measure
already points that way ("normal") or has to be flipped first ("invert").

If `CCA_indicator_list.csv` gains/loses/rewords a row, update the matching
entry here — a mismatch means this catalog is stale, not the CSV.
"""

from __future__ import annotations

from cca.scoring.engine import IndicatorMeta

CCA_INDICATORS: list[IndicatorMeta] = [
    # --- Health ---------------------------------------------------------
    # More doctors/nurses per person, more EmONC-capable facilities, more
    # skilled birth attendance, and more NHIMA registration are all more
    # capacity as-is.
    IndicatorMeta("health_doctor_to_population_ratio", "Health", "Supply", "normal"),
    IndicatorMeta("health_nurse_to_population_ratio", "Health", "Supply", "normal"),
    IndicatorMeta("health_facilities_with_functional_emonc", "Health", "Supply", "normal"),
    IndicatorMeta("health_skilled_birth_attendance_rate", "Health", "Access", "normal"),
    # A longer distance to the nearest facility is *less* access, so invert.
    IndicatorMeta("health_distance_to_nearest_facility", "Health", "Access", "invert"),
    IndicatorMeta("health_pct_population_registered_nhima", "Health", "Access", "normal"),
    # --- Education -------------------------------------------------------
    # A higher pupil-teacher ratio means each teacher is stretched over more
    # pupils, i.e. less capacity per pupil, so invert.
    IndicatorMeta("education_pupil_teacher_ratio_primary", "Education", "Supply", "invert"),
    IndicatorMeta("education_pupil_teacher_ratio_secondary", "Education", "Supply", "invert"),
    IndicatorMeta("education_electrification_of_schools", "Education", "Supply", "normal"),
    IndicatorMeta("education_schools_with_internet", "Education", "Supply", "normal"),
    # Longer travel time to school is less access, so invert.
    IndicatorMeta("education_distance_to_nearest_school", "Education", "Access", "invert"),
    IndicatorMeta("education_mean_years_of_schooling", "Education", "Access", "normal"),
    # --- Agriculture -------------------------------------------------------
    # Expressed as farmers per extension worker (e.g. MoA's stated 1:400);
    # a higher number means each worker covers more farmers, i.e. less
    # capacity per farmer, so invert.
    IndicatorMeta("agriculture_extension_worker_to_farmer_ratio", "Agriculture", "Supply", "invert"),
    IndicatorMeta("agriculture_maize_production_per_capita", "Agriculture", "Supply", "normal"),
    IndicatorMeta("agriculture_fra_storage_tonnes_per_capita", "Agriculture", "Supply", "normal"),
    IndicatorMeta("agriculture_pct_population_receiving_fisp", "Agriculture", "Access", "normal"),
    IndicatorMeta("agriculture_pct_farmers_reached_by_extension", "Agriculture", "Access", "normal"),
    # --- Infrastructure ------------------------------------------------
    IndicatorMeta("infrastructure_water_point_density", "Infrastructure", "Supply", "normal"),
    IndicatorMeta("infrastructure_grid_connection_capacity", "Infrastructure", "Supply", "normal"),
    IndicatorMeta("infrastructure_network_tower_coverage", "Infrastructure", "Supply", "normal"),
    IndicatorMeta("infrastructure_pct_households_safe_water", "Infrastructure", "Access", "normal"),
    # Longer time to the nearest water point is less access, so invert.
    IndicatorMeta("infrastructure_distance_to_nearest_water_point", "Infrastructure", "Access", "invert"),
    IndicatorMeta("infrastructure_pct_households_electrified", "Infrastructure", "Access", "normal"),
    # --- Environment (no Dimensions — ADR-0009) ---------------------------
    # Condition indicators: higher is already higher capacity.
    IndicatorMeta("environment_forest_cover", "Environment", None, "normal"),
    IndicatorMeta("environment_ecological_diversity", "Environment", None, "normal"),
    # Pressure indicators: higher raw value means more strain on the
    # environment's ability to sustain the population, i.e. less capacity,
    # so invert (ADR-0009).
    IndicatorMeta("environment_population_growth_rate", "Environment", None, "invert"),
    IndicatorMeta("environment_cattlehead_per_capita", "Environment", None, "invert"),
    IndicatorMeta("environment_charcoal_consumption_domestic", "Environment", None, "invert"),
]
