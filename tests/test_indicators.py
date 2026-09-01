from cca.scoring.indicators import CCA_INDICATORS

# Indicators where a higher raw value means *less* capacity, so the engine
# must invert them before normalisation. Kept here, independent of
# indicators.py's own comments, so an accidental edit there gets caught.
EXPECTED_INVERTED = {
    "health_distance_to_nearest_facility",
    "education_pupil_teacher_ratio_primary",
    "education_pupil_teacher_ratio_secondary",
    "education_distance_to_nearest_school",
    "agriculture_extension_worker_to_farmer_ratio",
    "infrastructure_distance_to_nearest_water_point",
    "environment_population_growth_rate",
    "environment_cattlehead_per_capita",
    "environment_charcoal_consumption_domestic",
}

SECTORS_WITH_DIMENSIONS = {"Health", "Education", "Agriculture", "Infrastructure"}


def test_indicator_ids_are_unique():
    ids = [i.indicator_id for i in CCA_INDICATORS]
    assert len(ids) == len(set(ids))


def test_orientation_matches_the_documented_pressure_and_ratio_indicators():
    inverted = {i.indicator_id for i in CCA_INDICATORS if i.orientation == "invert"}
    assert inverted == EXPECTED_INVERTED


def test_every_indicator_outside_environment_has_a_supply_or_access_dimension():
    for indicator in CCA_INDICATORS:
        if indicator.sector in SECTORS_WITH_DIMENSIONS:
            assert indicator.dimension in {"Supply", "Access"}, indicator.indicator_id


def test_environment_indicators_have_no_dimension():
    environment = [i for i in CCA_INDICATORS if i.sector == "Environment"]
    assert environment
    assert all(i.dimension is None for i in environment)


def test_only_the_five_cca_sectors_are_present():
    sectors = {i.sector for i in CCA_INDICATORS}
    assert sectors == {"Health", "Education", "Agriculture", "Infrastructure", "Environment"}
