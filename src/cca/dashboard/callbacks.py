"""Dash callback wiring for the CCA dashboard.

The `compute_*` functions do the actual read-and-shape work and take plain
arguments (an `Engine`, a district_code, ...) so they can be called directly
in tests without going through Dash's callback machinery (ADR-0010: this is
all reads + reshaping, never calculation). `register_callbacks` is the thin
layer that wires them to Dash `Input`/`Output`s.
"""

from __future__ import annotations

from dash import Dash, Input, Output, dash_table, html
from plotly import graph_objects as go
from sqlalchemy import Engine

from cca.dashboard.colors import SECTOR_RAMP
from cca.dashboard.data import (
    score_range,
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

# Zambia's approximate national extent — a fixed view, not fitted to
# locations, since the map never shows anything but all 116 Districts.
MAP_CENTER = {"lat": -13.5, "lon": 27.8}
MAP_ZOOM = 4.7


def compute_map_figure(engine: Engine, districts_df, geojson: dict, sector: str) -> go.Figure:
    sector_scores = read_latest_sector_scores(engine, sector=sector)
    merged = shape_map_data(sector_scores, districts_df)
    lo, hi = score_range(merged)

    fig = go.Figure(
        go.Choroplethmap(
            geojson=geojson,
            locations=merged["district_code"],
            z=merged["score"],
            featureidkey="id",
            zmin=lo,
            zmax=hi,
            colorscale=SECTOR_RAMP[sector],
            marker={"line": {"width": 0.4, "color": "white"}},
            customdata=merged[["name", "completeness_label"]],
            hovertemplate="<b>%{customdata[0]}</b><br>Score: %{z:.1f}<br>%{customdata[1]}<extra></extra>",
            colorbar={"title": {"text": f"{sector} Index"}},
        )
    )
    fig.update_layout(
        map_style="white-bg",
        map_center=MAP_CENTER,
        map_zoom=MAP_ZOOM,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        uirevision="keep",
    )
    return fig


def compute_subtitle(engine: Engine, sector: str) -> str:
    """The one-line subtitle: current Sector and the colour direction/range (ADR-0017)."""
    sector_scores = read_latest_sector_scores(engine, sector=sector)
    lo, hi = score_range(sector_scores)
    return (
        f"Showing {sector}. Darker = more capacity "
        f"(shaded across this Sector's range, {lo:.0f}-{hi:.0f}). Click a district for detail."
    )


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


def register_callbacks(app: Dash, engine: Engine, districts_df, geojson: dict) -> None:
    @app.callback(
        Output("map-graph", "figure"),
        Output("subtitle", "children"),
        Input("sector-select", "value"),
    )
    def _update_map(sector):
        return compute_map_figure(engine, districts_df, geojson, sector), compute_subtitle(engine, sector)
