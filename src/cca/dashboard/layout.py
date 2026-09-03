"""Static Dash layout for the CCA dashboard (map-hero, ADR-0020).

Every component a callback later updates is declared here up front with its
`id` (the standard Dash pattern) — callbacks only ever set a property on an
existing component, never recreate the component tree.
"""

from __future__ import annotations

import dash_mantine_components as dmc
from dash import dcc

RIGHT_COLUMN_PLACEHOLDER = dmc.Paper(
    withBorder=True,
    radius="md",
    p="md",
    children=dmc.Text(
        "Ranked district list — coming soon", size="sm", c="dimmed", ta="center"
    ),
)


def build_layout(sectors: list[str]) -> dmc.MantineProvider:
    sector_select = dmc.Select(
        id="sector-select",
        label="Sector",
        data=[{"label": sector, "value": sector} for sector in sectors],
        value=sectors[0] if sectors else None,
        allowDeselect=False,
        w=220,
    )

    return dmc.MantineProvider(
        forceColorScheme="light",
        children=dmc.AppShell(
            header={"height": 68},
            padding="md",
            children=[
                dmc.AppShellHeader(
                    px="md",
                    children=dmc.Group(
                        justify="space-between",
                        h="100%",
                        children=[
                            dmc.Stack(
                                gap=0,
                                justify="center",
                                children=[
                                    dmc.Title("Zambia Carrying Capacity Assessment", order=3),
                                    dmc.Text(id="subtitle", size="xs", c="dimmed"),
                                ],
                            ),
                            dmc.Anchor("Methodology", id="open-methodology", href="#", size="sm"),
                        ],
                    ),
                ),
                dmc.AppShellMain(
                    children=[
                        sector_select,
                        dmc.Grid(
                            gutter="md",
                            mt="md",
                            children=[
                                dmc.GridCol(
                                    span=8,
                                    children=dcc.Graph(
                                        id="map-graph",
                                        style={"height": "620px"},
                                        config={"displayModeBar": False},
                                    ),
                                ),
                                dmc.GridCol(span=4, children=RIGHT_COLUMN_PLACEHOLDER),
                            ],
                        ),
                    ]
                ),
            ],
        ),
    )
