"""PROTOTYPE — throwaway. v2 layout prototype for the CCA dashboard (map-hero).

Answers: what should the refined dashboard look like, and does it feel quick?
Settled model: WebGL no-tile map (big, left), ranked district rail (right),
per-district detail in a right Drawer. Per-sector hues; dark = high capacity.

Run:  ./.venv/Scripts/python.exe .scratch/cca-v2/prototype/app.py
Then open http://127.0.0.1:8055/

NOT production: no tests, no Postgres, synthetic data, minimal error handling.
"""

from __future__ import annotations

import dash
import dash_mantine_components as dmc
import numpy as np
import plotly.graph_objects as go
from dash import ALL, Input, Output, Patch, State, ctx, dcc, html

from synthetic import INDICATORS, SECTORS, Data, load_districts, load_geojson

# ---------------------------------------------------------------- data (once)
D = Data(load_districts())
CODES = D.codes
GEOJSON = load_geojson()

MEASURES = [
    {"label": "Overall", "value": "overall"},
    {"label": "Supply", "value": "supply"},
    {"label": "Access", "value": "access"},
]

# Per-sector single-hue sequential ramps, light (low capacity) -> dark (high).
# Distinct hues give each sector its own identity (red / blue / green / purple /
# amber). NOTE: not run through the dataviz CVD validator (no node here); chosen
# from a colourblind-aware base, and only one sector's map shows at a time.
SECTOR_RAMPS = {
    "Health": [[0.0, "#FCE9E6"], [0.5, "#E0806A"], [1.0, "#8C2D24"]],
    "Education": [[0.0, "#E7F0F8"], [0.5, "#6FA3D2"], [1.0, "#173F66"]],
    "Agriculture": [[0.0, "#E4F2EA"], [0.5, "#6FB894"], [1.0, "#1C5E41"]],
    "Infrastructure": [[0.0, "#EFEAF6"], [0.5, "#9E86C6"], [1.0, "#432C74"]],
    "Environment": [[0.0, "#FBF1DD"], [0.5, "#DBAA5A"], [1.0, "#7A5314"]],
}
SECTOR_DARK = {s: SECTOR_RAMPS[s][-1][1] for s in SECTORS}
AMBER = "#E8A33D"
MEASURE_LABEL = {"overall": "Overall", "supply": "Supply", "access": "Access"}


def z_values(sector, measure):
    arr = D.measure_array(sector, measure)
    return [None if np.isnan(v) else round(float(v), 1) for v in arr]


def z_range(sector, measure):
    arr = D.measure_array(sector, measure)
    valid = arr[~np.isnan(arr)]
    if valid.size == 0:
        return 0, 100
    lo, hi = float(valid.min()), float(valid.max())
    return (lo, hi) if hi > lo else (0, 100)


# ---------------------------------------------------------------- figures
def build_map_figure(sector, measure):
    lo, hi = z_range(sector, measure)
    fig = go.Figure(
        go.Choroplethmap(
            geojson=GEOJSON,
            locations=CODES,
            z=z_values(sector, measure),
            featureidkey="id",
            zmin=lo,
            zmax=hi,
            colorscale=SECTOR_RAMPS[sector],
            marker={"line": {"width": 0.4, "color": "white"}},
            colorbar={"title": {"text": f"{sector}<br>{MEASURE_LABEL[measure]}"}, "x": 0.99, "thickness": 12},
            customdata=[[D.name_by_code[c], "Complete" if D.is_complete(sector, c) else "Incomplete data"] for c in CODES],
            hovertemplate="<b>%{customdata[0]}</b><br>Score: %{z}<br>%{customdata[1]}<extra></extra>",
        )
    )
    fig.update_layout(map_style="white-bg", map_center={"lat": -13.5, "lon": 27.8}, map_zoom=4.7, margin={"l": 0, "r": 0, "t": 0, "b": 0}, uirevision="keep")
    return fig


def build_radar_figure(code):
    district = [D.measure_value(s, code, "overall") for s in SECTORS]
    natl = [D.national_average(s, "overall") for s in SECTORS]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=natl + [natl[0]], theta=SECTORS + [SECTORS[0]], name="National avg", fill="toself", opacity=0.3, line={"color": "#9AA7B1"}))
    fig.add_trace(go.Scatterpolar(r=district + [district[0]], theta=SECTORS + [SECTORS[0]], name=D.name_by_code[code], fill="toself", line={"color": "#0B4F4A"}, mode="lines+markers"))
    fig.update_layout(polar={"radialaxis": {"range": [0, 100], "visible": True}}, margin={"l": 40, "r": 40, "t": 20, "b": 30}, height=300, showlegend=True, legend={"orientation": "h", "y": -0.12})
    return fig


def build_compare_fig(sector, key, code):
    """This district vs all 116 on one indicator's RAW value; others grey, this
    one highlighted. National mean + optional NDP objective drawn as lines."""
    dist = D.indicator_distribution(sector, key)
    raw = dist["raw"]
    meta = D.meta[sector][key]
    i = CODES.index(code)
    this_val = raw[i]
    valid = ~np.isnan(raw)
    xs = raw[valid]
    # deterministic jitter so dots don't stack
    idx = np.arange(len(raw))[valid]
    ys = ((idx % 9) / 9.0 - 0.5) * 0.8

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", marker={"size": 6, "color": "#CBD5D5"}, hoverinfo="skip", showlegend=False))
    fig.add_vline(x=dist["mean"], line={"color": "#9AA7B1", "dash": "dot", "width": 1.5}, annotation_text="nat. avg", annotation_font_size=10, annotation_position="top")
    if meta["threshold"] is not None:
        fig.add_vline(x=meta["threshold"], line={"color": AMBER, "dash": "dash", "width": 2}, annotation_text="NDP objective", annotation_font_size=10, annotation_position="bottom")
    if not np.isnan(this_val):
        fig.add_trace(go.Scatter(x=[this_val], y=[0], mode="markers", marker={"size": 15, "color": SECTOR_DARK[sector], "line": {"color": "white", "width": 2}}, name=D.name_by_code[code], hovertemplate=f"%{{x}} {meta['unit']}<extra></extra>", showlegend=False))
    fig.update_layout(height=110, margin={"l": 8, "r": 8, "t": 14, "b": 24}, yaxis={"visible": False, "range": [-0.7, 0.7]}, xaxis={"title": {"text": meta["unit"], "font": {"size": 10}}, "ticks": "outside"}, plot_bgcolor="white")
    return fig


# ---------------------------------------------------------------- components
def completeness_dot(complete):
    if complete:
        return dmc.Box(w=8, h=8)
    return dmc.Tooltip(label="Computed from incomplete Indicators — treat with caution", children=dmc.Box(w=8, h=8, style={"borderRadius": "50%", "backgroundColor": AMBER}))


def ranked_rows(sector, measure):
    pairs = [(c, D.measure_value(sector, c, measure)) for c in CODES]
    pairs = [(c, s) for c, s in pairs if s is not None]
    pairs.sort(key=lambda r: r[1])
    out = []
    for rank, (code, s) in enumerate(pairs, 1):
        badge = dmc.Badge("Urban", size="xs", variant="light", color="gray") if code in D.urban else None
        out.append(
            html.Button(
                id={"type": "row", "code": code},
                n_clicks=0,
                className="rank-row",
                children=dmc.Group(
                    gap="sm",
                    wrap="nowrap",
                    children=[
                        dmc.Text(f"{rank}", size="sm", c="dimmed", w=22),
                        completeness_dot(D.is_complete(sector, code)),
                        dmc.Stack(
                            gap=2,
                            style={"flex": 1, "minWidth": 0},
                            children=[
                                dmc.Group(gap="xs", wrap="nowrap", children=[dmc.Text(D.name_by_code[code], size="sm", fw=500, truncate=True), badge]),
                                dmc.Progress(value=s, size="sm", color=SECTOR_DARK[sector]),
                            ],
                        ),
                        dmc.Text(f"{s:.0f}", size="sm", fw=700, w=30, ta="right"),
                    ],
                ),
            )
        )
    return out


def sa_legend_content(sector):
    if sector == "Environment":
        names = [i["name"] for i in INDICATORS[sector]]
        return dmc.Stack(gap=4, children=[dmc.Text("Environment has no Supply/Access split — its Indicators average directly:", size="xs", c="dimmed")] + [dmc.Text(f"• {n}", size="sm") for n in names])
    supply = [i["name"] for i in INDICATORS[sector] if i["dim"] == "Supply"]
    access = [i["name"] for i in INDICATORS[sector] if i["dim"] == "Access"]

    def col(title, items):
        return dmc.Stack(gap=2, children=[dmc.Text(title, size="xs", fw=700, tt="uppercase", c="dimmed")] + [dmc.Text(f"• {n}", size="sm") for n in items])
    return dmc.Group(align="flex-start", gap="xl", children=[col("Supply", supply), col("Access", access)])


def decomposition_cards(sector, code):
    cards = []
    for row in D.indicator_rows(sector, code):
        raw_txt = "—" if row["raw"] is None else f"{row['raw']:.1f} {row['unit']}"
        score_txt = "—" if row["score"] is None else f"{row['score']:.0f}"
        flag = None if row["score"] is not None else dmc.Badge("incomplete", size="xs", color="yellow", variant="light")
        header = dmc.Group(
            justify="space-between",
            align="flex-start",
            children=[
                dmc.Stack(gap=2, children=[dmc.Group(gap="xs", children=[dmc.Text(row["name"], fw=600, size="sm"), dmc.Badge(row["dim"], size="xs", variant="outline", color="gray"), flag]), dmc.Text(f"{row['ref_year']} · {row['source']}", size="xs", c="dimmed")]),
                dmc.Stack(gap=0, align="flex-end", children=[dmc.Text(raw_txt, fw=700, size="md"), dmc.Text(f"score {score_txt}", size="xs", c="dimmed")]),
            ],
        )
        body = dcc.Graph(figure=build_compare_fig(sector, row["key"], code), config={"displayModeBar": False}) if row["raw"] is not None else dmc.Text("No value reported for this district.", size="xs", c="dimmed")
        cards.append(dmc.Paper(withBorder=True, radius="md", p="sm", children=dmc.Stack(gap="xs", children=[header, body])))
    return dmc.Stack(gap="sm", children=cards)


def subtitle_text(sector, measure):
    lo, hi = z_range(sector, measure)
    return f"Showing {sector} — {MEASURE_LABEL[measure]}.  Darker = more capacity (shaded across this sector's range, {lo:.0f}–{hi:.0f}).  Click a district for detail."


# ---------------------------------------------------------------- layout
app = dash.Dash(__name__, suppress_callback_exceptions=True, title="CCA v2 prototype")

sector_select = dmc.Select(id="sector", label="Sector", data=[{"label": s, "value": s} for s in SECTORS], value=SECTORS[0], allowDeselect=False, w=190)
measure_control = dmc.Stack(
    gap=2,
    children=[
        dmc.Group(gap=4, children=[dmc.Text("Measure", size="sm", fw=500), dmc.HoverCard(withArrow=True, width=340, shadow="md", children=[dmc.HoverCardTarget(dmc.Text("ⓘ what's in Supply / Access?", size="xs", c="blue", style={"cursor": "help"})), dmc.HoverCardDropdown(id="sa-legend", children=sa_legend_content(SECTORS[0]))])]),
        dmc.SegmentedControl(id="measure", data=MEASURES, value="overall"),
    ],
)
controls = dmc.Group(align="flex-end", gap="lg", children=[sector_select, measure_control])

ranked_panel = dmc.Paper(
    withBorder=True,
    radius="md",
    p="xs",
    children=[
        dmc.Group(justify="space-between", px="xs", pt="xs", children=[dmc.Text("Districts, worst-served first", fw=600, size="sm"), dmc.Text("score", size="xs", c="dimmed")]),
        dmc.ScrollArea(h=600, children=dmc.Stack(id="ranked-list", gap=4, p="xs")),
    ],
)

app.layout = dmc.MantineProvider(
    forceColorScheme="light",
    children=[
        dcc.Store(id="sel-district"),
        dmc.AppShell(
            header={"height": 68},
            padding="md",
            children=[
                dmc.AppShellHeader(px="md", children=dmc.Group(justify="space-between", h="100%", children=[dmc.Stack(gap=0, justify="center", children=[dmc.Title("Zambia Carrying Capacity Assessment", order=3), dmc.Text("District-level sector capacity — v2 layout prototype", size="xs", c="dimmed")]), dmc.Anchor("Methodology", id="open-methodology", href="#", size="sm")])),
                dmc.AppShellMain(children=[
                    controls,
                    dmc.Text(id="subtitle", size="sm", c="dimmed", mt="xs", mb="md"),
                    dmc.Grid(gutter="md", children=[
                        dmc.GridCol(span=8, children=dcc.Graph(id="map-graph", style={"height": "620px"}, config={"displayModeBar": False})),
                        dmc.GridCol(span=4, children=ranked_panel),
                    ]),
                ]),
            ],
        ),
        dmc.Drawer(id="detail-drawer", position="right", size="xl", padding="md", title=dmc.Text(id="drawer-title", fw=700)),
        dmc.Drawer(id="methodology-drawer", position="right", size="md", padding="md", title=dmc.Text("Methodology", fw=700), children=dmc.Stack(gap="sm", children=[
            dmc.Text("Each Sector Index is a 0–100 score. Each Indicator is winsorised (1st/99th pct) then min-max normalised across all 116 districts, so scores are relative to the cohort, not a fixed benchmark.", size="sm"),
            dmc.Text("Indicators average within a Dimension (Supply / Access); Dimensions average within a Sector. Environment has no Dimensions — its Indicators average directly.", size="sm"),
            dmc.Alert("Why isn't the national average 50? Min-max only pins the lowest district to 0 and the highest to 100 — the mean sits wherever the distribution's mass is. Averaging several 0–100 Indicators into a Sector Index also pulls the spread toward the middle.", color="gray", variant="light", title="On the numbers"),
            dmc.Text("Darker = more capacity. The five Sector Indices are never combined into a single composite score.", size="sm"),
        ])),
    ],
)

app.index_string = app.index_string.replace(
    "</head>",
    """<style>
      .rank-row{all:unset;cursor:pointer;display:block;width:100%;padding:6px 8px;border-radius:8px;}
      .rank-row:hover{background:#F1F5F5;}
    </style></head>""",
)


# ---------------------------------------------------------------- callbacks
@app.callback(
    Output("map-graph", "figure"),
    Output("ranked-list", "children"),
    Output("subtitle", "children"),
    Output("sa-legend", "children"),
    Input("sector", "value"),
    Input("measure", "value"),
)
def _view(sector, measure):
    if ctx.triggered_id == "measure":
        # measure change within a sector: only z + range change -> Patch (no geometry resend)
        lo, hi = z_range(sector, measure)
        patched = Patch()
        patched["data"][0]["z"] = z_values(sector, measure)
        patched["data"][0]["zmin"] = lo
        patched["data"][0]["zmax"] = hi
        patched["data"][0]["colorbar"]["title"]["text"] = f"{sector}<br>{MEASURE_LABEL[measure]}"
        fig_out = patched
    else:
        # sector change (or first load): new hue ramp -> rebuild figure
        fig_out = build_map_figure(sector, measure)
    return fig_out, ranked_rows(sector, measure), subtitle_text(sector, measure), sa_legend_content(sector)


@app.callback(Output("measure", "data"), Output("measure", "value"), Input("sector", "value"), State("measure", "value"))
def _measure_availability(sector, current):
    if sector == "Environment":
        return [{"label": "Overall", "value": "overall"}], "overall"
    return MEASURES, (current or "overall")


@app.callback(
    Output("detail-drawer", "opened"),
    Output("detail-drawer", "children"),
    Output("drawer-title", "children"),
    Output("sel-district", "data"),
    Input("map-graph", "clickData"),
    Input({"type": "row", "code": ALL}, "n_clicks"),
    State("sector", "value"),
    prevent_initial_call=True,
)
def _open_detail(click_data, row_clicks, sector):
    trig = ctx.triggered_id
    code = None
    if trig == "map-graph" and click_data:
        code = click_data["points"][0]["location"]
    elif isinstance(trig, dict) and trig.get("type") == "row" and any(row_clicks or []):
        code = trig["code"]
    if not code:
        raise dash.exceptions.PreventUpdate

    urban_note = dmc.Alert("Mostly-urban district. A lower Agriculture score reflects urban land use, not an agricultural-capacity failure.", color="gray", variant="light", title="Urban") if code in D.urban else None
    children = dmc.Stack(gap="md", children=[
        urban_note,
        dmc.Text("Cross-sector profile — click an axis to switch the decomposition below", size="sm", fw=600),
        dcc.Graph(id="radar", figure=build_radar_figure(code), config={"displayModeBar": False}),
        dmc.Divider(),
        dmc.Group(gap="sm", align="flex-end", children=[dmc.Select(id="drawer-sector", label="Decompose sector", data=[{"label": s, "value": s} for s in SECTORS], value=sector, allowDeselect=False, w=220)]),
        html.Div(id="decomp-content", children=decomposition_cards(sector, code)),  # open by default
    ])
    return True, children, f"{D.name_by_code[code]}  ·  {D.prov_by_code[code]}", code


@app.callback(Output("drawer-sector", "value"), Input("radar", "clickData"), prevent_initial_call=True)
def _axis_to_sector(click_data):
    if not click_data:
        raise dash.exceptions.PreventUpdate
    theta = click_data["points"][0]["theta"]
    if theta not in SECTORS:
        raise dash.exceptions.PreventUpdate
    return theta


@app.callback(Output("decomp-content", "children", allow_duplicate=True), Input("drawer-sector", "value"), State("sel-district", "data"), prevent_initial_call=True)
def _decompose(sector, code):
    if not code:
        raise dash.exceptions.PreventUpdate
    return decomposition_cards(sector, code)


@app.callback(Output("methodology-drawer", "opened"), Input("open-methodology", "n_clicks"), prevent_initial_call=True)
def _open_methodology(n):
    return True


if __name__ == "__main__":
    app.run(debug=True, port=8055)
