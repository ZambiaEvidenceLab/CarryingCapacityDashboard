"""Light integration tests for the Dash app (testing decision in spec.md):

just enough to confirm the wiring works end to end against Postgres -- the
scoring math itself is covered by test_scoring_engine.py, not duplicated here.
"""

import dash_mantine_components as dmc
import pandas as pd
import pytest
from dash import dcc

from cca.dashboard.app import build_app
from cca.dashboard.callbacks import (
    _district_title,
    compute_decomposition_children,
    compute_indicator_compare_figure,
    compute_map_figure,
    compute_map_measure_patch,
    compute_radar_figure,
    compute_ranked_list,
    compute_subtitle,
    compute_summary_strip,
    compute_supply_access_legend,
)
from cca.dashboard.colors import AMBER, SECTOR_DARK, SECTOR_RAMP
from cca.dashboard.data import ACCESS, SUPPLY, build_district_geojson, score_range
from cca.grid3.client import District
from cca.scoring.engine import IndicatorMeta, run_scoring
from cca.storage.io import (
    read_districts,
    read_latest_dimension_scores,
    read_latest_sector_scores,
    write_district_master_list,
    write_indicator_metadata,
    write_scoring_run,
)


def _flatten_text(node) -> list[str]:
    """Every string appearing in a component tree's `children`, depth-first —
    lets a test assert on rendered text without pinning the exact nesting."""
    texts: list[str] = []
    if isinstance(node, (list, tuple)):
        for item in node:
            texts.extend(_flatten_text(item))
        return texts
    children = getattr(node, "children", None)
    if isinstance(children, str):
        texts.append(children)
    elif children is not None:
        texts.extend(_flatten_text(children))
    return texts

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
    write_indicator_metadata(
        clean_pg,
        INDICATOR_METAS,
        reference_years={
            "health_doctor_to_population_ratio": 2021,
            "health_distance_to_nearest_facility": 2020,
            "environment_forest_cover": 2019,
        },
        data_sources={
            "health_doctor_to_population_ratio": "MoH HR",
            "health_distance_to_nearest_facility": "GRID3",
            "environment_forest_cover": "MoL",
        },
        units={
            "health_doctor_to_population_ratio": "per 10k",
            "health_distance_to_nearest_facility": "km",
            "environment_forest_cover": "%",
        },
        # Only the doctor ratio carries an NDP objective; the others stay null so
        # the "absent target omits the line" path is exercised too (ticket 07).
        objectives={"health_doctor_to_population_ratio": 0.4},
    )
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

    def test_names_the_selected_measure(self, pg):
        assert "Supply" in compute_subtitle(pg, "Health", SUPPLY)


class TestMeasureRecolourAndRerank:
    """The Supply/Access segmented control (ticket 05)."""

    def _map(self, pg, sector, **kwargs):
        return compute_map_figure(
            pg, read_districts(pg), build_district_geojson(DISTRICT_RECORDS), DISTRICT_POINTS, sector, **kwargs
        )

    def test_map_recolours_to_the_dimensions_scores_and_range(self, pg):
        figure = self._map(pg, "Health", measure=SUPPLY)
        expected_lo, expected_hi = score_range(read_latest_dimension_scores(pg, "Health", SUPPLY))

        assert figure.data[0].zmin == pytest.approx(expected_lo)
        assert figure.data[0].zmax == pytest.approx(expected_hi)
        assert "Supply" in figure.data[0].colorbar.title.text

    def test_a_dimension_keeps_the_sectors_own_hue(self, pg):
        # Hue identifies the Sector, not the Measure — Supply and Overall share it.
        overall = self._map(pg, "Health")
        supply = self._map(pg, "Health", measure=SUPPLY)

        assert supply.data[0].colorscale == overall.data[0].colorscale

    def test_measure_patch_recolours_without_resending_geometry(self, pg):
        patch = compute_map_measure_patch(pg, read_districts(pg), DISTRICT_POINTS, "Health", SUPPLY)

        locations = [op["location"] for op in patch._operations]
        assert ["data", 0, "z"] in locations
        assert ["data", 0, "zmin"] in locations and ["data", 0, "zmax"] in locations
        # The boundary geometry is never re-attached on a Measure switch (ADR-0017
        # lever 3), and the selection halo (trace 1) is left untouched.
        assert all("geojson" not in location for location in locations)
        assert all(location[1] != 1 for location in locations)

    def test_completeness_overlay_tracks_the_displayed_measure(self, pg):
        # Deliberate deviation from the prototype's z-only Patch: per-Dimension
        # completeness genuinely differs, so the amber overlay must follow the
        # shown score. Health's Sector Index flags D3 (its Access Indicator is
        # missing), but the Supply Dimension (doctor ratio) is complete for all,
        # so switching to Supply must clear the overlay rather than leave D3's dot.
        overall = self._map(pg, "Health")
        assert list(overall.data[2].customdata) == ["D3"]

        supply_patch = compute_map_measure_patch(pg, read_districts(pg), DISTRICT_POINTS, "Health", SUPPLY)
        overlay = {
            tuple(op["location"]): op["params"]["value"]
            for op in supply_patch._operations
            if op["location"][:2] == ["data", 2]
        }
        assert overlay[("data", 2, "customdata")] == []
        assert overlay[("data", 2, "lat")] == [] and overlay[("data", 2, "lon")] == []

    def test_supply_access_reranks_the_list_by_that_dimension(self, pg):
        access_rows = compute_ranked_list(pg, read_districts(pg), "Health", measure=ACCESS)

        codes = [row.id["code"] for row in access_rows]
        # D3 has no Access Indicator, so it drops out of the Access ranking
        # (present in the Overall ranking, which ranks all three).
        assert set(codes) == {"D1", "D2"}
        expected = list(
            read_latest_dimension_scores(pg, "Health", ACCESS)
            .dropna(subset=["score"])
            .set_index("district_code")["score"]
            .sort_values()
            .index
        )
        assert codes == expected

    def test_environment_collapses_a_dimension_measure_to_overall(self, pg):
        # Environment has no Supply/Access scores (ADR-0003); a stale Dimension
        # measure must fall back to the Sector Index, not blank the view.
        env_map = self._map(pg, "Environment", measure=SUPPLY)
        assert env_map.data[0].colorbar.title.text == "Environment Index"

        supply_codes = [r.id["code"] for r in compute_ranked_list(pg, read_districts(pg), "Environment", measure=SUPPLY)]
        overall_codes = [r.id["code"] for r in compute_ranked_list(pg, read_districts(pg), "Environment")]
        assert supply_codes == overall_codes


class TestSaLegendContent:
    def test_split_sector_legend_has_a_supply_and_an_access_column(self):
        legend = compute_supply_access_legend("Health")

        headings = [column.children[0].children for column in legend.children]
        assert headings == [SUPPLY, ACCESS]

    def test_dimensionless_sector_legend_notes_the_no_split_case(self):
        legend = compute_supply_access_legend("Environment")

        note = legend.children[0].children
        assert "average directly" in note


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
    def test_health_shows_dimension_and_indicator_scores(self, pg):
        texts = _flatten_text(compute_decomposition_children(pg, "D1", "Health"))

        assert "Dimension scores" in texts and "Indicators" in texts
        assert SUPPLY in texts and ACCESS in texts  # the two Dimension rows
        assert "Doctor to population ratio" in texts  # humanised Indicator label

    def test_indicator_cards_show_reference_year_and_data_source(self, pg):
        texts = _flatten_text(compute_decomposition_children(pg, "D1", "Health"))

        assert any("2021" in text and "MoH HR" in text for text in texts)  # "2021 · MoH HR"

    def test_environment_has_no_dimension_section_only_indicators(self, pg):
        texts = _flatten_text(compute_decomposition_children(pg, "D1", "Environment"))

        assert "Dimension scores" not in texts
        assert "Indicators" in texts
        assert "Forest cover" in texts

    def test_an_incomplete_dimension_is_flagged(self, pg):
        # D3's Health Access Dimension is missing its only Indicator, so the
        # Dimension score is computed from incomplete Indicators.
        texts = _flatten_text(compute_decomposition_children(pg, "D3", "Health"))

        assert "incomplete" in texts

    def test_an_incomplete_sector_index_shows_a_completeness_alert(self, pg):
        # D3's Health Sector Index is incomplete (its Access Indicator is missing)
        # — the drawer must flag it so a dark-but-incomplete score isn't trusted.
        titles = _alert_titles(compute_decomposition_children(pg, "D3", "Health"))

        assert "Incomplete data" in titles

    def test_a_complete_sector_index_has_no_completeness_alert(self, pg):
        titles = _alert_titles(compute_decomposition_children(pg, "D1", "Health"))

        assert "Incomplete data" not in titles


def _alert_titles(children) -> list[str]:
    return [child.title for child in children if isinstance(child, dmc.Alert)]


def _graphs(node) -> list:
    """Every dcc.Graph in a component tree, depth-first."""
    found: list = []
    if isinstance(node, (list, tuple)):
        for item in node:
            found.extend(_graphs(item))
        return found
    if isinstance(node, dcc.Graph):
        found.append(node)
    children = getattr(node, "children", None)
    if children is not None and not isinstance(children, str):
        found.extend(_graphs(children))
    return found


class TestDecompositionRawValuesAndCompareCharts:
    """Ticket 07: raw values + compare-to-others charts in the Decomposition View."""

    def test_indicator_cards_show_the_raw_value_with_its_unit(self, pg):
        texts = _flatten_text(compute_decomposition_children(pg, "D1", "Health"))

        # D1's raw doctor-to-population ratio is 0.1 (per 10k) in _raw_values.
        assert any("0.1 per 10k" in text for text in texts)

    def test_indicator_cards_still_show_the_normalised_score(self, pg):
        texts = _flatten_text(compute_decomposition_children(pg, "D1", "Health"))

        assert any(text.startswith("score ") for text in texts)

    def test_each_indicator_with_a_value_gets_a_compare_chart(self, pg):
        children = compute_decomposition_children(pg, "D1", "Health")

        # D1 reported both Health Indicators, so both cards carry a chart.
        assert len(_graphs(children)) == 2

    def test_compare_chart_highlights_this_district_over_the_greyed_cohort(self, pg):
        figure = compute_indicator_compare_figure(pg, "Health", _doctor_row(pg, "D1"), "D1")

        # Trace 0 is the greyed cohort strip; the last trace is this District's
        # highlighted point in the Sector's dark hue at its own raw value (0.1).
        cohort_trace = figure.data[0]
        highlight = figure.data[-1]
        assert cohort_trace.marker.color == "#CBD5D5"
        assert highlight.marker.color == SECTOR_DARK["Health"]
        assert list(highlight.x) == [pytest.approx(0.1)]

    def test_compare_chart_marks_the_national_average(self, pg):
        figure = compute_indicator_compare_figure(pg, "Health", _doctor_row(pg, "D1"), "D1")

        # Cohort raw doctor ratios are 0.1 / 0.3 / 0.5 → mean 0.3, drawn as a line.
        avg_lines = [s for s in figure.layout.shapes if s.x0 == pytest.approx(0.3) and s.x0 == s.x1]
        assert avg_lines

    def test_compare_chart_draws_an_objective_line_when_the_catalog_has_one(self, pg):
        figure = compute_indicator_compare_figure(pg, "Health", _doctor_row(pg, "D1"), "D1")

        # The doctor ratio's NDP objective (0.4) is drawn as an amber line.
        objective_lines = [s for s in figure.layout.shapes if s.x0 == pytest.approx(0.4) and s.x0 == s.x1]
        assert objective_lines
        assert objective_lines[0].line.color == AMBER

    def test_compare_chart_omits_the_objective_line_when_absent(self, pg):
        # forest_cover has no objective in the fixture → only the nat-avg line.
        figure = compute_indicator_compare_figure(pg, "Environment", _forest_row(pg, "D1"), "D1")

        assert all(shape.line.color != AMBER for shape in figure.layout.shapes)

    def test_compare_chart_has_no_highlight_point_when_this_district_has_no_value(self, pg):
        # D3 never reported health_distance_to_nearest_facility, so its raw value
        # is absent — the cohort strip still draws, but no highlighted point.
        row = {"indicator_id": "health_distance_to_nearest_facility", "unit": "km", "objective": None}
        figure = compute_indicator_compare_figure(pg, "Health", row, "D3")

        # Only the cohort strip trace (D1, D2 reported it); no highlight trace.
        assert len(figure.data) == 1


def _indicator_row(pg, indicator_id: str, district_code: str) -> dict:
    from cca.storage.io import read_district_decomposition

    sector = {"health_doctor_to_population_ratio": "Health", "environment_forest_cover": "Environment"}[
        indicator_id
    ]
    values = read_district_decomposition(pg, district_code, sector)["indicator_values"].set_index(
        "indicator_id"
    )
    return {"indicator_id": indicator_id, **values.loc[indicator_id].to_dict()}


def _doctor_row(pg, district_code: str) -> dict:
    return _indicator_row(pg, "health_doctor_to_population_ratio", district_code)


def _forest_row(pg, district_code: str) -> dict:
    return _indicator_row(pg, "environment_forest_cover", district_code)


class TestDecompositionUrbanNote:
    def test_urban_district_decomposing_agriculture_gets_the_land_use_note(self, pg):
        titles = _alert_titles(compute_decomposition_children(pg, "D3", "Agriculture", is_urban=True))

        assert "Urban land use" in titles

    def test_note_absent_for_a_non_agriculture_sector(self, pg):
        titles = _alert_titles(compute_decomposition_children(pg, "D3", "Health", is_urban=True))

        assert "Urban land use" not in titles

    def test_note_absent_for_a_non_urban_district(self, pg):
        titles = _alert_titles(compute_decomposition_children(pg, "D1", "Agriculture", is_urban=False))

        assert "Urban land use" not in titles


class TestDistrictTitle:
    def test_formats_name_and_province(self, pg):
        assert _district_title(read_districts(pg), "D3") == "D3 City · P2"

    def test_falls_back_to_the_code_when_unknown(self, pg):
        assert _district_title(read_districts(pg), "NOPE") == "NOPE"


class TestBuildApp:
    def test_builds_a_dash_app_with_a_populated_layout(self, pg):
        app = build_app(pg, DISTRICT_RECORDS)

        assert app.layout is not None
