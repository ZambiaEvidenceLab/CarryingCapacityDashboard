"""Dash callback wiring for the CCA dashboard.

The `compute_*` functions do the actual read-and-shape work and take plain
arguments (an `Engine`, a district_code, ...) so they can be called directly
in tests without going through Dash's callback machinery (ADR-0010: this is
all reads + reshaping, never calculation). `register_callbacks` is the thin
layer that wires them to Dash `Input`/`Output`s.
"""

from __future__ import annotations

import dash_mantine_components as dmc
import pandas as pd
from dash import ALL, Dash, Input, Output, Patch, State, ctx, dcc, html
from dash.exceptions import PreventUpdate
from plotly import graph_objects as go
from sqlalchemy import Engine

from cca.dashboard.colors import AMBER, SECTOR_DARK, SECTOR_RAMP
from cca.dashboard.data import (
    MEASURES,
    OVERALL,
    OVERALL_ONLY,
    SECTORS_WITH_DIMENSIONS,
    SUPPLY,
    ACCESS,
    URBAN_AGRICULTURE_ANNOTATION,
    effective_measure,
    indicator_label,
    is_urban_district,
    score_range,
    sector_dimension_indicators,
    shape_compare_distribution,
    shape_decomposition,
    shape_map_data,
    shape_national_summary,
    shape_radar_data,
    shape_ranked_list,
)
from cca.storage.io import (
    read_district_decomposition,
    read_indicator_cohort_values,
    read_latest_dimension_scores,
    read_latest_sector_scores,
    read_national_summary,
    read_sector_cohort_values,
)

# Zambia's approximate national extent — a fixed view, not fitted to
# locations, since the map never shows anything but all 116 Districts.
MAP_CENTER = {"lat": -13.5, "lon": 27.8}
MAP_ZOOM = 4.7

# Map trace order: 0 = the choropleth; 1 = the selection halo; 2 = the
# Data-completeness dots. The two point overlays exist because `Choroplethmap`
# can't draw a per-District ring or hatch natively. Completeness is drawn *last*
# (on top) so a selected-yet-incomplete District still shows its amber signal
# rather than having it hidden under the halo. The Measure and selection
# callbacks Patch traces by index without rebuilding (ADR-0017 lever 3 — never
# resend geometry on a non-Sector change), so those indices are named.
_CHOROPLETH_TRACE = 0
_SELECTION_TRACE = 1
_COMPLETENESS_TRACE = 2

# The Sector whose low scores an Urban District's land use explains (CONTEXT.md).
# The land-use note is surfaced only when *this* Sector is decomposed (spec.md:
# contextual, not always-on noise), so the name is matched here by constant.
AGRICULTURE = "Agriculture"

# Fallback for a compare chart whose Indicator has no cohort rows at all — a
# defensive case (a listed Indicator always has at least this District's value),
# so `shape_compare_distribution` still gets the columns it reads.
_EMPTY_COHORT = pd.DataFrame(columns=["district_code", "raw_value"])


def _overlay_points(district_points: dict, codes) -> tuple[list[float], list[float]]:
    """Split a set of District codes into parallel lon/lat lists for a Scattermap overlay."""
    lons, lats = [], []
    for code in codes:
        point = district_points.get(code)
        if point is not None:
            lons.append(point[0])
            lats.append(point[1])
    return lons, lats


def _measure_scores(engine: Engine, sector: str, measure: str):
    """The scored rows for a Sector under one Measure: the Sector Index for
    Overall, else the named Supply/Access Dimension (ticket 05). `measure` is
    assumed already resolved by `effective_measure` (Environment → Overall)."""
    if measure == OVERALL:
        return read_latest_sector_scores(engine, sector=sector)
    return read_latest_dimension_scores(engine, sector, measure)


def _colorbar_title(sector: str, measure: str) -> str:
    """Colourbar heading: '<Sector> Index' for Overall, '<Sector><br><Measure>'
    for a Dimension, so the bar always names what the shading measures."""
    return f"{sector} Index" if measure == OVERALL else f"{sector}<br>{measure}"


def _incomplete_overlay(merged, district_points: dict):
    """The amber Data-completeness overlay's points for the displayed Measure:
    Districts that have a score but computed it from incomplete Indicators.

    Recomputed per Measure (not just per Sector) so switching to Supply/Access
    shows *that* Dimension's completeness — a District complete Overall can be
    incomplete on one Dimension, and the amber dot must track the shown score.
    """
    incomplete = merged[merged["score"].notna() & ~merged["complete"]]
    codes = list(incomplete["district_code"])
    lons, lats = _overlay_points(district_points, codes)
    names = merged.set_index("district_code").loc[codes, "name"].tolist() if codes else []
    return codes, lons, lats, names


def compute_map_figure(
    engine: Engine,
    districts_df,
    geojson: dict,
    district_points: dict,
    sector: str,
    selected_code: str | None = None,
    measure: str = OVERALL,
) -> go.Figure:
    measure = effective_measure(sector, measure)
    merged = shape_map_data(_measure_scores(engine, sector, measure), districts_df)
    lo, hi = score_range(merged)

    # Incomplete = has a score for the displayed Measure, but computed from
    # incomplete Indicators. A District with no score at all is a separate
    # "No data" case (blank fill), not flagged here — the overlay only stops a
    # *pale-but-incomplete* District being read as a confident low score (ticket 04).
    inc_codes, inc_lons, inc_lats, inc_names = _incomplete_overlay(merged, district_points)

    sel_lons, sel_lats = _overlay_points(
        district_points, [selected_code] if selected_code else []
    )

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
            colorbar={"title": {"text": _colorbar_title(sector, measure)}},
        )
    )
    # Trace 1 — selected-District highlight: a translucent halo in the Sector's
    # dark hue, drawn *under* the completeness dots so it never hides the amber
    # signal. Empty until a District is picked. `hoverinfo="skip"` lets a click on
    # a selected complete District fall through to the choropleth beneath.
    fig.add_trace(
        go.Scattermap(
            lat=sel_lats,
            lon=sel_lons,
            mode="markers",
            marker={"size": 22, "color": SECTOR_DARK[sector], "opacity": 0.5},
            hoverinfo="skip",
            name="Selected",
            showlegend=False,
        )
    )
    # Trace 2 — Data-completeness overlay (amber dots on incomplete Districts).
    # `customdata` carries the District code so a click landing on the dot (it
    # sits on the District's centroid) still selects that District.
    fig.add_trace(
        go.Scattermap(
            lat=inc_lats,
            lon=inc_lons,
            mode="markers",
            marker={"size": 9, "color": AMBER},
            text=inc_names,
            customdata=inc_codes,
            hovertemplate="<b>%{text}</b><br>Incomplete data<extra></extra>",
            name="Incomplete data",
            showlegend=False,
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


def compute_map_measure_patch(
    engine: Engine, districts_df, district_points: dict, sector: str, measure: str
) -> Patch:
    """A partial map update for a Measure switch within a Sector (ticket 05).

    Only the choropleth's `z`/range/colourbar and the amber completeness overlay
    change — the boundary `geojson` is never re-attached, so the geometry is not
    re-sent (ADR-0017 lever 3, the single biggest v1 speed regression). The
    selection halo (trace 1) is untouched: a Measure switch never changes Sector,
    so its hue and the selected District both stay put.
    """
    measure = effective_measure(sector, measure)
    merged = shape_map_data(_measure_scores(engine, sector, measure), districts_df)
    lo, hi = score_range(merged)
    inc_codes, inc_lons, inc_lats, inc_names = _incomplete_overlay(merged, district_points)

    patched = Patch()
    patched["data"][_CHOROPLETH_TRACE]["z"] = merged["score"].tolist()
    patched["data"][_CHOROPLETH_TRACE]["zmin"] = lo
    patched["data"][_CHOROPLETH_TRACE]["zmax"] = hi
    patched["data"][_CHOROPLETH_TRACE]["customdata"] = merged[["name", "completeness_label"]].values.tolist()
    patched["data"][_CHOROPLETH_TRACE]["colorbar"]["title"]["text"] = _colorbar_title(sector, measure)
    patched["data"][_COMPLETENESS_TRACE]["lat"] = inc_lats
    patched["data"][_COMPLETENESS_TRACE]["lon"] = inc_lons
    patched["data"][_COMPLETENESS_TRACE]["text"] = inc_names
    patched["data"][_COMPLETENESS_TRACE]["customdata"] = inc_codes
    return patched


def _completeness_dot(complete: bool):
    """An amber Data-completeness dot when a score used incomplete Indicators; a
    same-size spacer when complete, so every row's columns stay aligned."""
    if complete:
        return dmc.Box(w=8, h=8)
    return dmc.Tooltip(
        label="Sector Index computed from incomplete Indicators — treat with caution",
        withArrow=True,
        children=dmc.Box(w=8, h=8, style={"borderRadius": "50%", "backgroundColor": AMBER}),
    )


def _ranked_row(row: dict, sector: str, selected_code: str | None):
    """One ranked-list row: rank · Data-completeness dot · name (+ Urban chip) ·
    Sector Index microbar · score. The whole row is a button that selects the
    District (map + list stay in step, ticket 04)."""
    code = row["district_code"]
    urban_chip = (
        dmc.Badge("Urban", size="xs", variant="light", color="gray") if row["is_urban"] else None
    )
    selected = code == selected_code
    return html.Button(
        id={"type": "rank-row", "code": code},
        n_clicks=0,
        className="rank-row rank-row--selected" if selected else "rank-row",
        style={"borderLeft": f"3px solid {SECTOR_DARK[sector]}"} if selected else None,
        children=dmc.Group(
            gap="sm",
            wrap="nowrap",
            children=[
                dmc.Text(f"{row['rank']}", size="sm", c="dimmed", w=22),
                _completeness_dot(row["complete"]),
                dmc.Stack(
                    gap=2,
                    style={"flex": 1, "minWidth": 0},
                    children=[
                        dmc.Group(
                            gap="xs",
                            wrap="nowrap",
                            children=[
                                dmc.Text(row["name"], size="sm", fw=500, truncate=True),
                                urban_chip,
                            ],
                        ),
                        dmc.Progress(value=row["score"], size="sm", color=SECTOR_DARK[sector]),
                    ],
                ),
                dmc.Text(f"{row['score']:.0f}", size="sm", fw=700, w=30, ta="right"),
            ],
        ),
    )


def compute_ranked_list(
    engine: Engine, districts_df, sector: str, selected_code: str | None = None, measure: str = OVERALL
) -> list:
    """The ranked-district-list rows for one Sector and Measure, worst-served
    first (tickets 04, 05) — Supply/Access re-rank by that Dimension's scores."""
    measure = effective_measure(sector, measure)
    rows = shape_ranked_list(_measure_scores(engine, sector, measure), districts_df)
    return [_ranked_row(row, sector, selected_code) for row in rows]


def compute_subtitle(engine: Engine, sector: str, measure: str = OVERALL) -> str:
    """The one-line subtitle: current Sector, Measure, and the colour direction/range (ADR-0017)."""
    measure = effective_measure(sector, measure)
    lo, hi = score_range(_measure_scores(engine, sector, measure))
    return (
        f"Showing {sector} — {measure}. Darker = more capacity "
        f"(shaded across this Sector's range, {lo:.0f}-{hi:.0f}). Click a district for detail."
    )


def compute_supply_access_legend(sector: str):
    """The 'what's in Supply / Access?' hover contents for a Sector (ticket 05):
    two columns of the Sector's Supply and Access Indicators, or — for a
    dimension-less Sector (Environment, ADR-0003) — a note that its Indicators
    average directly with no split."""
    grouped = sector_dimension_indicators(sector)

    if set(grouped) == {None}:  # dimension-less Sector: a single un-split list
        return dmc.Stack(
            gap=4,
            children=[
                dmc.Text(
                    f"{sector} has no Supply/Access split — its Indicators average directly:",
                    size="xs",
                    c="dimmed",
                ),
                *[dmc.Text(f"• {name}", size="sm") for name in grouped[None]],
            ],
        )

    def _column(dimension: str):
        return dmc.Stack(
            gap=2,
            children=[
                dmc.Text(dimension, size="xs", fw=700, tt="uppercase", c="dimmed"),
                *[dmc.Text(f"• {name}", size="sm") for name in grouped.get(dimension, [])],
            ],
        )

    return dmc.Group(align="flex-start", gap="xl", children=[_column(SUPPLY), _column(ACCESS)])


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


def _score_text(score) -> str:
    """A 0-100 score as a whole number, or an em dash when it's absent."""
    return "—" if score is None or pd.isna(score) else f"{float(score):.0f}"


def _incomplete_badge(complete: bool):
    """A small 'incomplete' badge when a score used incomplete Indicators."""
    if complete:
        return None
    return dmc.Badge("incomplete", size="xs", color="yellow", variant="light")


def _dimension_row(row: dict):
    """One Dimension (Supply/Access) score line: name, incomplete flag, score."""
    return dmc.Group(
        justify="space-between",
        children=[
            dmc.Group(
                gap="xs",
                children=[dmc.Text(row["dimension"], size="sm", fw=500), _incomplete_badge(row["complete"])],
            ),
            dmc.Text(_score_text(row["score"]), size="sm", fw=700),
        ],
    )


def _indicator_meta_line(row: dict) -> str:
    """'reference year · data source', dropping either part when it's not set."""
    year = row.get("reference_year")
    parts = []
    if pd.notna(year):
        parts.append(str(int(year)))
    if pd.notna(row.get("data_source")):
        parts.append(str(row["data_source"]))
    return " · ".join(parts)


def _with_unit(text_value: str, unit) -> str:
    """Append the Indicator's unit to a rendered value, or leave it bare when the
    catalog carries no unit for it yet (nullable metadata field)."""
    return f"{text_value} {unit}" if pd.notna(unit) else text_value


def _raw_value_text(raw, unit) -> str:
    """A raw Indicator value with its unit (e.g. '12.3 per 10k'), or an em dash
    when the District reported no value."""
    if raw is None or pd.isna(raw):
        return "—"
    return _with_unit(f"{float(raw):.1f}", unit)


def _build_compare_figure(sector: str, row: dict, dist: dict) -> go.Figure:
    """The compare-to-others chart for one Indicator (ticket 07): every District's
    raw value as a greyed strip, this District highlighted in the Sector's dark
    hue, the national average as a dotted line, and — where the catalog carries a
    raw-unit NDP objective — that target as a labelled amber line.

    A deterministic vertical jitter spreads the strip so overlapping raw values
    don't stack into one dot; it isn't data, only separation."""
    values = dist["values"]
    unit = row.get("unit")
    objective = row.get("objective")

    # Deterministic vertical jitter (no RNG, so the strip is stable across
    # re-renders): spread points over 9 evenly-spaced rows within +/-0.4 of the
    # centre line, comfortably inside the axis's [-0.7, 0.7] range so the larger
    # highlighted point at y=0 still stands clear.
    ys = [((i % 9) / 9.0 - 0.5) * 0.8 for i in range(len(values))]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=values,
            y=ys,
            mode="markers",
            marker={"size": 6, "color": "#CBD5D5"},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    if dist["mean"] is not None:
        fig.add_vline(
            x=dist["mean"],
            line={"color": "#9AA7B1", "dash": "dot", "width": 1.5},
            annotation_text="nat. avg",
            annotation_font_size=10,
            annotation_position="top",
        )
    if pd.notna(objective):
        fig.add_vline(
            x=float(objective),
            line={"color": AMBER, "dash": "dash", "width": 2},
            annotation_text="NDP objective",
            annotation_font_size=10,
            annotation_position="bottom",
        )
    if dist["this_value"] is not None:
        # `%{x:.1f}` matches the card's raw-value precision; `_with_unit` appends
        # the same unit label the card shows (or nothing when the catalog has none).
        fig.add_trace(
            go.Scatter(
                x=[dist["this_value"]],
                y=[0],
                mode="markers",
                marker={"size": 15, "color": SECTOR_DARK[sector], "line": {"color": "white", "width": 2}},
                hovertemplate=_with_unit("%{x:.1f}", unit) + "<extra></extra>",
                showlegend=False,
            )
        )
    fig.update_layout(
        height=110,
        margin={"l": 8, "r": 8, "t": 14, "b": 24},
        yaxis={"visible": False, "range": [-0.7, 0.7]},
        xaxis={"title": {"text": unit, "font": {"size": 10}} if pd.notna(unit) else {}, "ticks": "outside"},
        plot_bgcolor="white",
    )
    return fig


def compute_indicator_compare_figure(engine: Engine, sector: str, row: dict, district_code: str) -> go.Figure:
    """Read one Indicator's cohort raw values and build its compare-to-others chart.

    Split from `_build_compare_figure` so the read (a per-Indicator cohort query)
    stays out of the pure figure assembly — the figure is a display reshape of
    already-scored raw values, never a calculation (ADR-0010)."""
    cohort = read_indicator_cohort_values(engine, row["indicator_id"])
    dist = shape_compare_distribution(district_code, cohort)
    return _build_compare_figure(sector, row, dist)


def _indicator_card(row: dict, compare_figure: go.Figure | None):
    """One Indicator's card (ticket 07): label (+ Dimension badge), reference year
    and data source, the **raw value with its unit** (with the 0-100 normalised
    score beneath it), and the compare-to-others chart. A District that reported
    no value for the Indicator shows a clear 'no value reported' note instead of
    a chart (dropped-not-imputed, ADR-0007/0008)."""
    dimension = row.get("dimension")
    dim_badge = (
        dmc.Badge(dimension, size="xs", variant="outline", color="gray") if pd.notna(dimension) else None
    )
    meta_line = _indicator_meta_line(row)
    header = dmc.Group(
        justify="space-between",
        align="flex-start",
        wrap="nowrap",
        children=[
            dmc.Stack(
                gap=2,
                children=[
                    dmc.Group(
                        gap="xs",
                        children=[dmc.Text(indicator_label(row["indicator_id"]), fw=600, size="sm"), dim_badge],
                    ),
                    dmc.Text(meta_line, size="xs", c="dimmed") if meta_line else None,
                ],
            ),
            dmc.Stack(
                gap=0,
                align="flex-end",
                children=[
                    dmc.Text(_raw_value_text(row.get("raw_value"), row.get("unit")), fw=700, size="md"),
                    dmc.Text(f"score {_score_text(row.get('value'))}", size="xs", c="dimmed"),
                ],
            ),
        ],
    )
    if compare_figure is not None:
        body = dcc.Graph(figure=compare_figure, config={"displayModeBar": False})
    else:
        body = dmc.Text("No value reported for this District.", size="xs", c="dimmed")
    return dmc.Paper(withBorder=True, radius="md", p="sm", children=dmc.Stack(gap="xs", children=[header, body]))


def compute_decomposition_children(
    engine: Engine, district_code: str, sector: str, is_urban: bool = False
) -> list:
    """The Decomposition View for one District and Sector (tickets 06, 07).

    Shows the Sector's Dimension scores (Supply/Access) and, per Indicator, its
    raw value with unit, its 0-100 normalised score, and a compare-to-others
    chart of every District's raw value with this one highlighted, the national
    average, and any NDP objective (ticket 07). Each Indicator's reference year
    and data source appear on its card. Environment has no Dimensions (ADR-0003),
    so the Dimension section is omitted and Indicators sit directly under the
    Sector Index. A mostly-urban District decomposing Agriculture gets the
    land-use note, surfaced only in that context (spec.md)."""
    breakdown = read_district_decomposition(engine, district_code, sector)
    shaped = shape_decomposition(district_code, sector, breakdown)

    # One read for the whole Sector's compare-to-others charts, grouped by
    # Indicator, rather than a query per Indicator card (this Sector's Indicators
    # are ~5-6, and the drawer opens on demand — but the batched read keeps the
    # decomposition path off an N+1).
    cohort_by_indicator = {
        indicator_id: group for indicator_id, group in read_sector_cohort_values(engine, sector).groupby("indicator_id")
    }

    children: list = []
    if is_urban and sector == AGRICULTURE:
        children.append(
            dmc.Alert(URBAN_AGRICULTURE_ANNOTATION, title="Urban land use", color="gray", variant="light")
        )

    # A Sector-level completeness flag, so a dark-but-incomplete District is not
    # read as a confident score (spec.md). Placed here because Environment has no
    # Dimension rows to carry the per-Dimension flag below (ADR-0003).
    if not shaped["sector_complete"]:
        children.append(
            dmc.Alert(
                "This Sector Index is computed from incomplete Indicators — some are missing "
                "for this District. Treat it with caution.",
                title="Incomplete data",
                color="yellow",
                variant="light",
            )
        )

    if shaped["dimensions"]:
        children.append(dmc.Text("Dimension scores", fw=600, size="sm"))
        children.append(dmc.Stack(gap="xs", children=[_dimension_row(row) for row in shaped["dimensions"]]))

    children.append(dmc.Text("Indicators", fw=600, size="sm"))
    cards = []
    for row in shaped["indicators"]:
        # A listed Indicator normally carries a raw value (a missing one is
        # dropped, so it has no row at all); the chart is omitted defensively
        # when a raw value is somehow absent, and always tolerates this District
        # not being in the cohort (no highlighted point).
        raw = row.get("raw_value")
        if raw is not None and not pd.isna(raw):
            cohort = cohort_by_indicator.get(row["indicator_id"], _EMPTY_COHORT)
            figure = _build_compare_figure(sector, row, shape_compare_distribution(district_code, cohort))
        else:
            figure = None
        cards.append(_indicator_card(row, figure))
    children.append(dmc.Stack(gap="sm", children=cards))
    return children


def _district_title(districts_df, district_code: str) -> str:
    """'<name> · <province>' for the drawer header, or the bare code if unknown."""
    row = districts_df.loc[districts_df["district_code"] == district_code]
    if row.empty:
        return district_code
    return f"{row.iloc[0]['name']} · {row.iloc[0]['province']}"


def register_callbacks(
    app: Dash, engine: Engine, districts_df, geojson: dict, district_points: dict, sectors: list[str]
) -> None:
    @app.callback(
        Output("measure", "data"),
        Output("measure", "value"),
        Output("measure", "disabled"),
        Output("sa-legend", "children"),
        Input("sector-select", "value"),
        State("measure", "value"),
    )
    def _configure_measure_control(sector, current):
        # A dimension-less Sector (Environment, ADR-0003) has no Supply/Access
        # scores, so the control collapses to Overall-only *and* is disabled —
        # only Overall applies (ticket 05). Every other Sector keeps its current
        # Measure across the switch. The hover legend re-lists the new Sector's
        # Indicators either way.
        legend = compute_supply_access_legend(sector)
        if sector not in SECTORS_WITH_DIMENSIONS:
            return OVERALL_ONLY, OVERALL, True, legend
        return MEASURES, (current or OVERALL), False, legend

    @app.callback(
        Output("map-graph", "figure"),
        Output("subtitle", "children"),
        Input("sector-select", "value"),
        Input("measure", "value"),
        State("selected-district", "data"),
        State("map-graph", "figure"),
    )
    def _render_map(sector, measure, selected_code, existing_figure):
        # A Measure switch within a Sector only recolours — Patch the z/range and
        # completeness overlay, never re-send the geometry (ADR-0017 lever 3). A
        # Sector change rebuilds: a new Sector means a new hue ramp. Selection is
        # read from State (not an Input) so picking a District never lands here
        # and never resends geometry; that path patches the halo.
        #
        # A Patch can only recolour a figure that already exists. On first load
        # the map has no figure yet, and `_configure_measure_control` writes
        # `measure.value` during that same initial render — which makes `measure`
        # the trigger here, not `sector-select`. Without the `existing_figure`
        # guard the first render would take the Patch branch and land on an empty
        # graph, leaving the default Sector's map blank until the user switches
        # Sectors (which forces a full rebuild). Guarding on an existing figure
        # forces a full build whenever there's nothing to patch — first load, or
        # any Measure-triggered render that somehow precedes a build.
        subtitle = compute_subtitle(engine, sector, measure)
        if ctx.triggered_id == "measure" and existing_figure:
            patch = compute_map_measure_patch(engine, districts_df, district_points, sector, measure)
            return patch, subtitle
        figure = compute_map_figure(
            engine, districts_df, geojson, district_points, sector, selected_code, measure
        )
        return figure, subtitle

    @app.callback(
        Output("ranked-list", "children"),
        Input("sector-select", "value"),
        Input("measure", "value"),
        Input("selected-district", "data"),
    )
    def _render_ranked_list(sector, measure, selected_code):
        # Re-renders on a Sector switch or Measure switch (re-rank) or a selection
        # change (re-apply the row highlight). Cheap — it touches no geometry,
        # only list rows.
        return compute_ranked_list(engine, districts_df, sector, selected_code, measure)

    @app.callback(
        Output("selected-district", "data"),
        Input("map-graph", "clickData"),
        Input({"type": "rank-row", "code": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def _select_district(click_data, _row_clicks):
        # The shared selection both the map and the list (and ticket 06's Drawer)
        # read from. A District is selected the same way whether the user clicks
        # it on the map or clicks its row.
        trigger = ctx.triggered_id
        if trigger == "map-graph":
            # Choropleth points carry `location`; the amber completeness dot sits
            # on a District's centroid and carries the code in `customdata` — read
            # either so clicking the marked centre of a District still selects it.
            point = (click_data or {}).get("points", [{}])[0]
            code = point.get("location") or point.get("customdata")
            if not code:
                raise PreventUpdate
            return code
        if isinstance(trigger, dict) and trigger.get("type") == "rank-row":
            # A list re-render resets each row's n_clicks to 0 and fires this
            # callback; ignore those, act only on a real click (n_clicks > 0).
            if not ctx.triggered[0]["value"]:
                raise PreventUpdate
            return trigger["code"]
        raise PreventUpdate

    @app.callback(
        Output("map-graph", "figure", allow_duplicate=True),
        Input("selected-district", "data"),
        prevent_initial_call=True,
    )
    def _highlight_map_selection(selected_code):
        # Move the selection halo to the picked District via Patch — only the
        # overlay trace's points change, the choropleth geometry is left intact.
        # The halo's hue is already correct for the current Sector (set on the
        # last figure build; a selection change never changes Sector), so only
        # lat/lon move here.
        lons, lats = _overlay_points(district_points, [selected_code] if selected_code else [])
        patched = Patch()
        patched["data"][_SELECTION_TRACE]["lat"] = lats
        patched["data"][_SELECTION_TRACE]["lon"] = lons
        return patched

    @app.callback(
        Output("detail-drawer", "opened"),
        Output("drawer-title", "children"),
        Output("drawer-urban-note", "children"),
        Output("radar", "figure"),
        Output("drawer-sector", "value"),
        Input("selected-district", "data"),
        State("sector-select", "value"),
        prevent_initial_call=True,
    )
    def _open_district_drawer(selected_code, sector):
        # Selecting a District slides the drawer in over the scan (ticket 06). It
        # sets the radar and the decomposed-Sector Select to the Sector on the map;
        # setting that value drives `_render_decomposition`, so the Decomposition
        # View shows immediately with no second click. The scan underneath keeps
        # its selection — closing the drawer (DMC's own close) never clears it.
        if not selected_code:
            raise PreventUpdate
        urban = is_urban_district(districts_df, selected_code)
        urban_chip = dmc.Badge("Urban", size="sm", variant="light", color="gray") if urban else None
        radar = compute_radar_figure(engine, sectors, selected_code)
        return True, _district_title(districts_df, selected_code), urban_chip, radar, sector

    @app.callback(
        Output("drawer-sector", "value", allow_duplicate=True),
        Input("radar", "clickData"),
        prevent_initial_call=True,
    )
    def _axis_to_decomposed_sector(click_data):
        # Clicking a radar axis switches which Sector the decomposition covers —
        # the axis label is a Sector name, so it feeds straight into the Select.
        theta = (click_data or {}).get("points", [{}])[0].get("theta")
        if theta not in sectors:
            raise PreventUpdate
        return theta

    @app.callback(
        Output("decomp-content", "children"),
        Input("drawer-sector", "value"),
        Input("selected-district", "data"),
        prevent_initial_call=True,
    )
    def _render_decomposition(sector, selected_code):
        # Re-renders whenever the decomposed Sector changes (radar axis or the
        # in-drawer Select) or a new District is picked. Both are Inputs so a
        # new District with an unchanged Sector still refreshes the breakdown.
        if not selected_code or not sector:
            raise PreventUpdate
        is_urban = is_urban_district(districts_df, selected_code)
        return compute_decomposition_children(engine, selected_code, sector, is_urban=is_urban)
