"""Light integration tests for the Dash app (testing decision in spec.md):

just enough to confirm the wiring works end to end against Postgres -- the
scoring math itself is covered by test_scoring_engine.py, not duplicated here.
"""

import pandas as pd
import pytest

from cca.dashboard.app import build_app
from cca.dashboard.callbacks import (
    compute_decomposition_children,
    compute_map_figure,
    compute_radar_figure,
    compute_ranked_list,
    compute_subtitle,
    compute_summary_strip,
)
from cca.dashboard.colors import SECTOR_RAMP
from cca.dashboard.data import build_district_geojson, score_range
from cca.grid3.client import District
from cca.scoring.engine import IndicatorMeta, run_scoring
from cca.storage.io import (
    read_districts,
    read_latest_sector_scores,
    write_district_master_list,
    write_scoring_run,
)

DISTRICTS = ["D1", "D2", "D3"]

def _square(x: float, y: float) -> dict:
    return {"type": "Polygon", "coordinates": [[[x, y], [x + 1, y], [x + 1, y + 1], [x, y + 1], [x, y]]]}


DISTRICT_RECORDS = [
    District(code="D1", name="D1 Town", province="P1", province_code="PC1", geometry=_square(28.0, -15.0)),
    District(code="D2", name="D2 Town", province="P1", province_code="PC1", geometry=_square(29.0, -14.0)),
    District(code="D3", name="D3 City", province="P2", province_code="PC2", geometry=_square(30.0, -13.0)),
]

INDICATOR_METAS = [
    IndicatorMeta("health_doctor_to_population_ratio", "Health", "Supply"),
    IndicatorMeta("health_distance_to_nearest_facility", "Health", "Access", "invert"),
    IndicatorMeta("environment_forest_cover", "Environment", None),
]

SECTORS = ["Health", "Environment"]

# Representative points for the map overlays. Hand-built rather than derived from
# the (empty) test geometries above — the overlay callbacks only need a point
# per code, and shapely isn't exercised here (it has its own coverage).
DISTRICT_POINTS = {"D1": (28.0, -14.0), "D2": (29.0, -13.0), "D3": (30.0, -12.0)}


def _raw_values() -> pd.DataFrame:
    rows = [
        {"district_code": "D1", "indicator_id": "health_doctor_to_population_ratio", "value": 0.1},
        {"district_code": "D2", "indicator_id": "health_doctor_to_population_ratio", "value": 0.3},
        {"district_code": "D3", "indicator_id": "health_doctor_to_population_ratio", "value": 0.5},
        {"district_code": "D1", "indicator_id": "health_distance_to_nearest_facility", "value": 20.0},
        {"district_code": "D2", "indicator_id": "health_distance_to_nearest_facility", "value": 10.0},
        # D3's health_distance_to_nearest_facility is deliberately missing,
        # so its Health Sector Index comes back incomplete.
        {"district_code": "D1", "indicator_id": "environment_forest_cover", "value": 40.0},
        {"district_code": "D2", "indicator_id": "environment_forest_cover", "value": 60.0},
        {"district_code": "D3", "indicator_id": "environment_forest_cover", "value": 80.0},
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def pg(clean_pg):
    write_district_master_list(clean_pg, DISTRICT_RECORDS, urban_district_names=frozenset({"D3 City"}))
    write_scoring_run(clean_pg, run_scoring(_raw_values(), INDICATOR_METAS, DISTRICTS), INDICATOR_METAS)
    return clean_pg


class TestComputeMapFigure:
    def test_shapes_one_row_per_district_for_the_selected_sector(self, pg):
        districts_df = read_districts(pg)
        geojson = build_district_geojson(DISTRICT_RECORDS)

        figure = compute_map_figure(pg, districts_df, geojson, DISTRICT_POINTS, "Health")

        trace = figure.data[0]
        assert sorted(trace.locations) == DISTRICTS
        assert trace.geojson == geojson

    def test_uses_a_webgl_choroplethmap_trace_with_no_basemap(self, pg):
        districts_df = read_districts(pg)
        geojson = build_district_geojson(DISTRICT_RECORDS)

        figure = compute_map_figure(pg, districts_df, geojson, DISTRICT_POINTS, "Health")

        assert figure.data[0].type == "choroplethmap"
        assert figure.layout.map.style == "white-bg"

    def test_colours_with_the_selected_sectors_own_hue_ramp(self, pg):
        districts_df = read_districts(pg)
        geojson = build_district_geojson(DISTRICT_RECORDS)

        health_figure = compute_map_figure(pg, districts_df, geojson, DISTRICT_POINTS, "Health")
        environment_figure = compute_map_figure(pg, districts_df, geojson, DISTRICT_POINTS, "Environment")

        assert list(health_figure.data[0].colorscale) == [tuple(stop) for stop in SECTOR_RAMP["Health"]]
        assert health_figure.data[0].colorscale != environment_figure.data[0].colorscale

    def test_colour_range_is_the_sectors_live_min_max_not_a_fixed_0_100(self, pg):
        districts_df = read_districts(pg)
        geojson = build_district_geojson(DISTRICT_RECORDS)
        expected_lo, expected_hi = score_range(read_latest_sector_scores(pg, sector="Health"))

        figure = compute_map_figure(pg, districts_df, geojson, DISTRICT_POINTS, "Health")

        assert figure.data[0].zmin == pytest.approx(expected_lo)
        assert figure.data[0].zmax == pytest.approx(expected_hi)


class TestMapOverlays:
    def test_incomplete_districts_get_a_completeness_overlay_marker(self, pg):
        # D3's Health Sector Index is incomplete (its Access Indicator is missing).
        districts_df = read_districts(pg)
        geojson = build_district_geojson(DISTRICT_RECORDS)

        figure = compute_map_figure(pg, districts_df, geojson, DISTRICT_POINTS, "Health")

        assert len(figure.data) == 3  # choropleth + selection + completeness overlays
        completeness = figure.data[2]  # drawn last, on top of the selection halo
        assert list(completeness.lon) == [DISTRICT_POINTS["D3"][0]]
        assert list(completeness.lat) == [DISTRICT_POINTS["D3"][1]]
        assert list(completeness.customdata) == ["D3"]  # click on the dot selects D3

    def test_selection_overlay_is_empty_until_a_district_is_selected(self, pg):
        districts_df = read_districts(pg)
        geojson = build_district_geojson(DISTRICT_RECORDS)

        unselected = compute_map_figure(pg, districts_df, geojson, DISTRICT_POINTS, "Health")
        selected = compute_map_figure(pg, districts_df, geojson, DISTRICT_POINTS, "Health", "D2")

        assert list(unselected.data[1].lon) == []
        assert list(selected.data[1].lon) == [DISTRICT_POINTS["D2"][0]]


class TestComputeRankedList:
    def test_ranks_scored_districts_worst_served_first(self, pg):
        districts_df = read_districts(pg)

        rows = compute_ranked_list(pg, districts_df, "Health")

        codes = [row.id["code"] for row in rows]
        assert set(codes) == set(DISTRICTS)
        assert codes[0] == "D1"  # lowest Health Sector Index → most underserved → rank 1

    def test_switching_sector_reranks_by_that_sectors_scores(self, pg):
        districts_df = read_districts(pg)

        environment = [row.id["code"] for row in compute_ranked_list(pg, districts_df, "Environment")]

        # The list re-queries the selected Sector and orders by its own scores
        # ascending, not Health's.
        expected = list(
            read_latest_sector_scores(pg, sector="Environment")
            .set_index("district_code")["score"]
            .sort_values()
            .index
        )
        assert environment == expected

    def test_the_selected_row_is_highlighted(self, pg):
        districts_df = read_districts(pg)

        rows = compute_ranked_list(pg, districts_df, "Health", selected_code="D2")

        selected = next(row for row in rows if row.id["code"] == "D2")
        other = next(row for row in rows if row.id["code"] == "D1")
        assert "rank-row--selected" in selected.className
        assert "rank-row--selected" not in other.className


class TestComputeSubtitle:
    def test_names_the_current_sector_and_the_colour_direction(self, pg):
        subtitle = compute_subtitle(pg, "Health")

        assert "Health" in subtitle
        assert "Darker = more capacity" in subtitle

    def test_states_the_sectors_live_range_shown(self, pg):
        lo, hi = score_range(read_latest_sector_scores(pg, sector="Health"))

        subtitle = compute_subtitle(pg, "Health")

        assert f"{lo:.0f}-{hi:.0f}" in subtitle


class TestComputeSummaryStrip:
    def test_reports_the_low_completeness_count_for_the_selected_sector(self, pg):
        children = compute_summary_strip(pg, "Health")

        rendered = " ".join(child.children for child in children)
        assert "Districts with low data completeness: 1" in rendered


class TestComputeRadarFigure:
    def test_one_trace_per_district_and_national_average_across_the_given_sectors(self, pg):
        figure = compute_radar_figure(pg, SECTORS, "D1")

        assert len(figure.data) == 2
        assert list(figure.data[0].theta) == SECTORS
        assert figure.data[1].name == "National average"


class TestComputeDecompositionChildren:
    def test_health_sector_includes_dimension_and_indicator_tables(self, pg):
        children = compute_decomposition_children(pg, "D1", "Health")

        table_data = [c.data for c in children if hasattr(c, "data")]
        assert any(row.get("dimension") == "Supply" for rows in table_data for row in rows)
        assert any(row.get("indicator_id") == "health_doctor_to_population_ratio" for rows in table_data for row in rows)

    def test_environment_sector_has_no_dimension_table_only_indicators(self, pg):
        children = compute_decomposition_children(pg, "D1", "Environment")

        headings = [c.children for c in children if hasattr(c, "children") and isinstance(c.children, str)]
        assert "Dimension scores" not in headings

        table_data = [c.data for c in children if hasattr(c, "data")]
        assert any(row.get("indicator_id") == "environment_forest_cover" for rows in table_data for row in rows)


class TestBuildApp:
    def test_builds_a_dash_app_with_a_populated_layout(self, pg):
        app = build_app(pg, DISTRICT_RECORDS)

        assert app.layout is not None
