import pandas as pd

from cca.dashboard.data import (
    ACCESS,
    OVERALL,
    SUPPLY,
    URBAN_AGRICULTURE_ANNOTATION,
    build_district_geojson,
    build_district_points,
    effective_measure,
    indicator_label,
    is_urban_district,
    score_range,
    sector_dimension_indicators,
    shape_decomposition,
    shape_map_data,
    shape_national_summary,
    shape_radar_data,
    shape_ranked_list,
)
from cca.grid3.client import District

DISTRICTS_DF = pd.DataFrame(
    [
        {"district_code": "D1", "name": "D1 Town", "is_urban": False},
        {"district_code": "D2", "name": "D2 City", "is_urban": True},
    ]
)


class TestBuildDistrictGeojson:
    def test_keys_each_feature_by_district_code(self):
        districts = [
            District(code="D1", name="D1 Town", province="P1", province_code="PC1", geometry={"type": "Polygon"}),
        ]

        geojson = build_district_geojson(districts)

        assert geojson["type"] == "FeatureCollection"
        feature = geojson["features"][0]
        assert feature["id"] == "D1"
        assert feature["geometry"] == {"type": "Polygon"}
        assert feature["properties"]["name"] == "D1 Town"


class TestShapeMapData:
    def test_merges_scores_with_district_names_and_urban_flag(self):
        scores = pd.DataFrame([{"district_code": "D1", "sector": "Health", "score": 42.0, "complete": True}])

        merged = shape_map_data(scores, DISTRICTS_DF).set_index("district_code")

        assert merged.loc["D1", "name"] == "D1 Town"
        assert bool(merged.loc["D1", "is_urban"]) is False
        assert merged.loc["D1", "completeness_label"] == "Complete"

    def test_a_district_with_no_scored_row_yet_still_appears_on_the_map(self):
        scores = pd.DataFrame([{"district_code": "D1", "sector": "Health", "score": 42.0, "complete": True}])

        merged = shape_map_data(scores, DISTRICTS_DF).set_index("district_code")

        assert pd.isna(merged.loc["D2", "score"])
        assert merged.loc["D2", "completeness_label"] == "Incomplete data"


class TestShapeRankedList:
    SCORES = pd.DataFrame(
        [
            {"district_code": "D1", "sector": "Health", "score": 70.0, "complete": True},
            {"district_code": "D2", "sector": "Health", "score": 30.0, "complete": False},
        ]
    )

    def test_ranks_scored_districts_worst_served_first(self):
        rows = shape_ranked_list(self.SCORES, DISTRICTS_DF)

        # Ascending by score: the lowest (most underserved) District ranks 1.
        assert [(r["rank"], r["district_code"]) for r in rows] == [(1, "D2"), (2, "D1")]

    def test_each_row_carries_name_score_completeness_and_urban_flag(self):
        rows = shape_ranked_list(self.SCORES, DISTRICTS_DF)
        by_code = {r["district_code"]: r for r in rows}

        assert by_code["D2"]["name"] == "D2 City"
        assert by_code["D2"]["score"] == 30.0
        assert by_code["D2"]["complete"] is False
        assert by_code["D2"]["is_urban"] is True
        assert by_code["D1"]["complete"] is True
        assert by_code["D1"]["is_urban"] is False

    def test_a_district_with_no_score_for_this_sector_is_excluded(self):
        # A District absent from the Sector's scores (no Sector Index yet) does
        # not get a rank — the list is the ranking of *scored* Districts.
        scores = pd.DataFrame(
            [{"district_code": "D1", "sector": "Health", "score": 70.0, "complete": True}]
        )

        rows = shape_ranked_list(scores, DISTRICTS_DF)

        assert [r["district_code"] for r in rows] == ["D1"]


class TestBuildDistrictPoints:
    def test_returns_a_lon_lat_point_inside_each_districts_polygon(self):
        districts = [
            District(
                code="D1",
                name="D1 Town",
                province="P1",
                province_code="PC1",
                geometry={
                    "type": "Polygon",
                    "coordinates": [[[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0], [0.0, 0.0]]],
                },
            )
        ]

        points = build_district_points(districts)

        lon, lat = points["D1"]
        assert 0.0 < lon < 2.0
        assert 0.0 < lat < 2.0


class TestScoreRange:
    def test_returns_the_live_min_and_max_of_present_scores(self):
        scores = pd.DataFrame([{"score": 20.0}, {"score": 80.0}, {"score": 50.0}])

        assert score_range(scores) == (20.0, 80.0)

    def test_ignores_missing_scores(self):
        scores = pd.DataFrame([{"score": 20.0}, {"score": None}, {"score": 80.0}])

        assert score_range(scores) == (20.0, 80.0)

    def test_falls_back_to_0_100_when_every_score_is_missing(self):
        scores = pd.DataFrame([{"score": None}, {"score": None}])

        assert score_range(scores) == (0.0, 100.0)

    def test_falls_back_to_0_100_when_every_present_score_is_identical(self):
        # zmin == zmax would flatten the colourscale to a single shade.
        scores = pd.DataFrame([{"score": 50.0}, {"score": 50.0}])

        assert score_range(scores) == (0.0, 100.0)


class TestShapeNationalSummary:
    def test_rounds_present_values(self):
        summary = shape_national_summary({"average": 42.345, "spread": 5.678, "incomplete_count": 3})

        assert summary == {"average": 42.3, "spread": 5.7, "incomplete_count": 3}

    def test_handles_an_empty_run_with_no_scores(self):
        summary = shape_national_summary({"average": None, "spread": None, "incomplete_count": 0})

        assert summary == {"average": None, "spread": None, "incomplete_count": 0}


class TestShapeRadarData:
    ALL_SCORES = pd.DataFrame(
        [
            {"district_code": "D1", "sector": "Health", "score": 80.0, "complete": True},
            {"district_code": "D2", "sector": "Health", "score": 40.0, "complete": True},
            {"district_code": "D1", "sector": "Education", "score": 60.0, "complete": False},
        ]
    )

    def test_aligns_district_and_national_average_scores_to_the_sector_axis_order(self):
        radar = shape_radar_data("D1", self.ALL_SCORES, ["Health", "Education", "Environment"])

        assert radar["sectors"] == ["Health", "Education", "Environment"]
        assert radar["district_scores"] == [80.0, 60.0, None]
        assert radar["national_average_scores"] == [60.0, 60.0, None]

    def test_flags_a_dimension_computed_from_incomplete_indicators(self):
        radar = shape_radar_data("D1", self.ALL_SCORES, ["Health", "Education"])

        assert radar["district_complete"] == [True, False]

    def test_a_district_missing_from_a_sector_entirely_shows_none_not_a_dropped_axis(self):
        radar = shape_radar_data("D2", self.ALL_SCORES, ["Health", "Education"])

        assert radar["district_scores"] == [40.0, None]
        assert radar["district_complete"] == [True, False]


class TestShapeDecomposition:
    def test_environment_has_no_dimension_rows_only_indicator_rows(self):
        breakdown = {
            "dimensions": pd.DataFrame(columns=["dimension", "score", "complete"]),
            "indicator_values": pd.DataFrame(
                [{"indicator_id": "environment_forest_cover", "value": 70.0, "reference_year": 2022}]
            ),
        }

        shaped = shape_decomposition("D1", "Environment", breakdown)

        assert shaped["dimensions"] == []
        assert shaped["indicators"] == [
            {"indicator_id": "environment_forest_cover", "value": 70.0, "reference_year": 2022}
        ]

    def test_a_supply_access_sector_returns_both_dimension_and_indicator_rows(self):
        breakdown = {
            "dimensions": pd.DataFrame(
                [
                    {"dimension": "Supply", "score": 50.0, "complete": True},
                    {"dimension": "Access", "score": 30.0, "complete": True},
                ]
            ),
            "indicator_values": pd.DataFrame(
                [{"indicator_id": "health_doctor_to_population_ratio", "value": 50.0, "reference_year": 2021}]
            ),
        }

        shaped = shape_decomposition("D1", "Health", breakdown)

        assert len(shaped["dimensions"]) == 2
        assert len(shaped["indicators"]) == 1


class TestIsUrbanDistrict:
    def test_true_for_a_flagged_district(self):
        assert is_urban_district(DISTRICTS_DF, "D2") is True

    def test_false_for_an_unflagged_district(self):
        assert is_urban_district(DISTRICTS_DF, "D1") is False

    def test_false_for_a_district_not_in_the_master_list(self):
        assert is_urban_district(DISTRICTS_DF, "UNKNOWN") is False


def test_urban_annotation_text_mentions_agriculture():
    assert "Agriculture" in URBAN_AGRICULTURE_ANNOTATION


class TestEffectiveMeasure:
    def test_keeps_a_dimension_for_a_sector_that_has_dimensions(self):
        assert effective_measure("Health", SUPPLY) == SUPPLY
        assert effective_measure("Health", ACCESS) == ACCESS

    def test_collapses_a_dimension_to_overall_for_a_dimensionless_sector(self):
        # Environment has no Supply/Access split (ADR-0003), so a Dimension
        # measure can't apply — it resolves to Overall (the Sector Index).
        assert effective_measure("Environment", SUPPLY) == OVERALL

    def test_a_blank_or_overall_measure_stays_overall(self):
        assert effective_measure("Health", None) == OVERALL
        assert effective_measure("Health", OVERALL) == OVERALL


class TestIndicatorLabel:
    def test_drops_the_sector_prefix_and_humanises(self):
        assert indicator_label("health_doctor_to_population_ratio") == "Doctor to population ratio"

    def test_handles_an_id_without_an_underscore(self):
        assert indicator_label("forest") == "Forest"


class TestSectorDimensionIndicators:
    def test_groups_a_sectors_indicators_by_supply_and_access(self):
        grouped = sector_dimension_indicators("Health")

        assert set(grouped) == {SUPPLY, ACCESS}
        assert "Doctor to population ratio" in grouped[SUPPLY]
        assert "Distance to nearest facility" in grouped[ACCESS]

    def test_a_dimensionless_sector_groups_under_a_single_none_key(self):
        grouped = sector_dimension_indicators("Environment")

        assert set(grouped) == {None}
        assert "Forest cover" in grouped[None]
