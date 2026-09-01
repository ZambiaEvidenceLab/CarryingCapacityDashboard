"""Static Dash layout for the CCA dashboard.

Every component a callback later updates is declared here up front with its
`id` (the standard Dash pattern) — callbacks only ever set a property on an
existing component, never recreate the component tree.
"""

from __future__ import annotations

from dash import dash_table, dcc, html

from cca.dashboard.faq import GENERAL_FAQ, build_indicator_faq_rows


def _general_faq_section() -> html.Div:
    return html.Div(
        [html.Details([html.Summary(question), html.P(answer)]) for question, answer in GENERAL_FAQ]
    )


def _indicator_faq_table(indicator_catalog) -> html.Div:
    rows = build_indicator_faq_rows(indicator_catalog)
    return html.Div(
        [
            html.H4("Which Indicators feed which Sector"),
            dash_table.DataTable(
                id="faq-indicator-table",
                columns=[
                    {"name": "Sector", "id": "sector"},
                    {"name": "Dimension", "id": "dimension"},
                    {"name": "Indicator", "id": "indicator_id"},
                    {"name": "Reference year", "id": "reference_year"},
                    {"name": "Data source", "id": "data_source"},
                ],
                data=rows,
                style_cell={"textAlign": "left", "padding": "6px"},
                style_header={"fontWeight": "bold"},
            ),
        ]
    )


def build_layout(sectors: list[str], indicator_catalog) -> html.Div:
    return html.Div(
        [
            html.H1("Zambia Carrying Capacity Assessment"),
            dcc.Store(id="selected-district-store"),
            html.Div(
                [
                    html.Label("Sector"),
                    dcc.Dropdown(
                        id="sector-dropdown",
                        options=[{"label": sector, "value": sector} for sector in sectors],
                        value=sectors[0] if sectors else None,
                        clearable=False,
                    ),
                ],
                style={"maxWidth": "300px"},
            ),
            html.Div(id="summary-strip"),
            dcc.Graph(id="choropleth-map"),
            html.Div(
                id="district-section",
                style={"display": "none"},
                children=[
                    html.H2(id="district-heading"),
                    html.Div(id="urban-annotation"),
                    dcc.Graph(id="radar-chart"),
                ],
            ),
            html.Div(
                id="decomposition-section",
                style={"display": "none"},
                children=[
                    html.H3(id="decomposition-heading"),
                    html.Div(id="decomposition-content"),
                ],
            ),
            html.Hr(),
            html.H2("Methodology FAQ"),
            _general_faq_section(),
            _indicator_faq_table(indicator_catalog),
        ]
    )
