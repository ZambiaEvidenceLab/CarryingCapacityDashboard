"""Dash callback wiring for the CCA dashboard.

The `compute_*` functions do the actual read-and-shape work and take plain
arguments (an `Engine`, a district_code, ...) so they can be called directly
in tests without going through Dash's callback machinery (ADR-0010: this is
all reads + reshaping, never calculation). `register_callbacks` is the thin
layer that wires them to Dash `Input`/`Output`s.
"""

from __future__ import annotations

from dash import Dash, Input, Output, State, dash_table, html
from plotly import graph_objects as go
from sqlalchemy import Engine

from cca.dashboard.data import (
    URBAN_AGRICULTURE_ANNOTATION,
    is_urban_district,
    shape_decomposition,
    shape_map_data,
    shape_national_summary,
    shape_radar_data,
)
from cca.storage.io import (
    read_district_decomposition,
    read_latest_sector_scores,
    read_national_summary,
)


def _clicked_point_value(click_data: dict | None, key: str) -> str | None:
    """Pull one field off a Plotly `clickData` event's first point, or None if nothing was clicked."""
    if not click_data:
        return None
    return click_data["points"][0][key]


def compute_map_figure(engine: Engine, districts_df, geojson: dict, sector: str) -> go.Figure:
    sector_scores = read_latest_sector_scores(engine, sector=sector)
    merged = shape_map_data(sector_scores, districts_df)

    fig = go.Figure(
        go.Choropleth(
            geojson=geojson,
            locations=merged["district_code"],
            z=merged["score"],
            zmin=0,
            zmax=100,
            colorscale="Viridis",
            marker_line_width=0.5,
            customdata=merged[["name", "completeness_label"]],
            hovertemplate="%{customdata[0]}<br>Score: %{z:.1f}<br>%{customdata[1]}<extra></extra>",
            colorbar_title=f"{sector} Index",
        )
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin={"l": 0, "r": 0, "t": 0, "b": 0})
    return fig


def compute_summary_strip(engine: Engine, sector: str) -> list:
    summary = shape_national_summary(read_national_summary(engine, sector))
    average = "n/a" if summary["average"] is None else summary["average"]
    spread = "n/a" if summary["spread"] is None else summary["spread"]
    return [
        html.Span(f"National average: {average}", style={"marginRight": "24px"}),
        html.Span(f"Spread (std dev): {spread}", style={"marginRight": "24px"}),
        html.Span(f"Districts with low data completeness: {summary['incomplete_count']}"),
    ]


def compute_radar_figure(engine: Engine, sectors: list[str], district_code: str) -> go.Figure:
    all_scores = read_latest_sector_scores(engine)
    radar = shape_radar_data(district_code, all_scores, sectors)
    completeness_text = [
        "Data completeness: complete" if complete else "Data completeness: incomplete"
        for complete in radar["district_complete"]
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=radar["district_scores"],
            theta=radar["sectors"],
            fill="toself",
            name=district_code,
            mode="lines+markers",
            text=completeness_text,
            hovertemplate="%{theta}: %{r}<br>%{text}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=radar["national_average_scores"],
            theta=radar["sectors"],
            fill="toself",
            name="National average",
            opacity=0.5,
        )
    )
    fig.update_layout(polar={"radialaxis": {"range": [0, 100]}})
    return fig


def compute_decomposition_children(engine: Engine, district_code: str, sector: str) -> list:
    breakdown = read_district_decomposition(engine, district_code, sector)
    shaped = shape_decomposition(district_code, sector, breakdown)

    children = []
    if shaped["dimensions"]:
        children.append(html.H4("Dimension scores"))
        children.append(
            dash_table.DataTable(
                columns=[
                    {"name": "Dimension", "id": "dimension"},
                    {"name": "Score", "id": "score"},
                    {"name": "Complete", "id": "complete"},
                ],
                data=shaped["dimensions"],
            )
        )

    children.append(html.H4("Indicator scores"))
    children.append(
        dash_table.DataTable(
            columns=[
                {"name": "Indicator", "id": "indicator_id"},
                {"name": "Value", "id": "value"},
                {"name": "Reference year", "id": "reference_year"},
                {"name": "Data source", "id": "data_source"},
            ],
            data=shaped["indicators"],
        )
    )
    return children


def register_callbacks(app: Dash, engine: Engine, districts_df, geojson: dict, sectors: list[str]) -> None:
    @app.callback(
        Output("choropleth-map", "figure"),
        Output("summary-strip", "children"),
        Input("sector-dropdown", "value"),
    )
    def _update_map(sector):
        return compute_map_figure(engine, districts_df, geojson, sector), compute_summary_strip(engine, sector)

    @app.callback(
        Output("district-section", "style"),
        Output("district-heading", "children"),
        Output("urban-annotation", "children"),
        Output("radar-chart", "figure"),
        Output("selected-district-store", "data"),
        Output("decomposition-section", "style"),
        Input("choropleth-map", "clickData"),
        prevent_initial_call=True,
    )
    def _select_district(click_data):
        district_code = _clicked_point_value(click_data, "location")
        if district_code is None:
            return {"display": "none"}, None, None, go.Figure(), None, {"display": "none"}

        name_row = districts_df.loc[districts_df["district_code"] == district_code]
        name = name_row.iloc[0]["name"] if not name_row.empty else district_code

        annotation = URBAN_AGRICULTURE_ANNOTATION if is_urban_district(districts_df, district_code) else None
        radar_figure = compute_radar_figure(engine, sectors, district_code)
        # A newly selected district hides any Decomposition View left open
        # from the previous district's radar chart.
        return (
            {"display": "block"},
            f"{name} ({district_code})",
            annotation,
            radar_figure,
            district_code,
            {"display": "none"},
        )

    @app.callback(
        Output("decomposition-section", "style", allow_duplicate=True),
        Output("decomposition-heading", "children"),
        Output("decomposition-content", "children"),
        Input("radar-chart", "clickData"),
        State("selected-district-store", "data"),
        prevent_initial_call=True,
    )
    def _select_sector_axis(click_data, district_code):
        sector = _clicked_point_value(click_data, "theta")
        if sector is None or not district_code:
            return {"display": "none"}, None, None

        return (
            {"display": "block"},
            f"{sector} decomposition for {district_code}",
            compute_decomposition_children(engine, district_code, sector),
        )
