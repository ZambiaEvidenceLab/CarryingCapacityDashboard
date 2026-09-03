"""Static Dash layout for the CCA dashboard (map-hero, ADR-0020).

Every component a callback later updates is declared here up front with its
`id` (the standard Dash pattern) — callbacks only ever set a property on an
existing component, never recreate the component tree.
"""

from __future__ import annotations

import dash_mantine_components as dmc
from dash import dcc

from cca.dashboard.data import MEASURES, OVERALL

RANKED_LIST_PANEL = dmc.Paper(
    withBorder=True,
    radius="md",
    p="xs",
    children=[
        dmc.Group(
            justify="space-between",
            px="xs",
            pt="xs",
            children=[
                dmc.Text("Districts, worst-served first", fw=600, size="sm"),
                dmc.Text("Sector Index", size="xs", c="dimmed"),
            ],
        ),
        # Rows are rendered by the ranked-list callback (they depend on the
        # scored run, which the static layout has no access to). Empty here;
        # the Sector-select callback fills it on first load.
        dmc.ScrollArea(h=600, children=dmc.Stack(id="ranked-list", gap=4, p="xs")),
    ],
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

    # Overall · Supply · Access — recolours the map and re-ranks the list to the
    # chosen Dimension (ticket 05). `data` and `value` are reset by the
    # measure-control callback (Overall-only for a dimension-less Sector); the
    # `sa-legend` hover lists the current Sector's Supply/Access Indicators, also
    # filled by that callback. Both start empty and are populated on first load.
    measure_control = dmc.Stack(
        gap=2,
        children=[
            dmc.Group(
                gap=4,
                children=[
                    dmc.Text("Measure", size="sm", fw=500),
                    dmc.HoverCard(
                        withArrow=True,
                        width=340,
                        shadow="md",
                        children=[
                            dmc.HoverCardTarget(
                                dmc.Text(
                                    "ⓘ what's in Supply / Access?",
                                    size="xs",
                                    c="blue",
                                    style={"cursor": "help"},
                                )
                            ),
                            dmc.HoverCardDropdown(id="sa-legend", children=[]),
                        ],
                    ),
                ],
            ),
            dmc.SegmentedControl(id="measure", data=MEASURES, value=OVERALL),
        ],
    )

    # Within-District detail (ticket 06, ADR-0020): a right Drawer that slides in
    # over the scan. Its inner containers are declared here up front (radar,
    # decomposed-Sector Select, decomposition container, Urban-chip container);
    # the selection callback fills them and the Decomposition View shows by default.
    detail_drawer = dmc.Drawer(
        id="detail-drawer",
        position="right",
        size="xl",
        padding="md",
        opened=False,
        title=dmc.Text(id="drawer-title", fw=700),
        children=dmc.Stack(
            gap="md",
            children=[
                dmc.Box(id="drawer-urban-note"),
                dmc.Text(
                    "Cross-sector profile — click an axis to switch the decomposition below",
                    size="sm",
                    fw=600,
                ),
                dcc.Graph(id="radar", style={"height": "320px"}, config={"displayModeBar": False}),
                dmc.Divider(),
                dmc.Select(
                    id="drawer-sector",
                    label="Decompose Sector",
                    data=[{"label": sector, "value": sector} for sector in sectors],
                    allowDeselect=False,
                    w=240,
                ),
                dmc.Box(id="decomp-content"),
            ],
        ),
    )

    return dmc.MantineProvider(
        forceColorScheme="light",
        children=[
          dcc.Store(id="selected-district"),
          detail_drawer,
          dmc.AppShell(
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
                        dmc.Group(align="flex-end", gap="lg", children=[sector_select, measure_control]),
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
                                dmc.GridCol(span=4, children=RANKED_LIST_PANEL),
                            ],
                        ),
                    ]
                ),
            ],
          ),
        ],
    )
