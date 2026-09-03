"""Static Dash layout for the CCA dashboard (map-hero, ADR-0020).

Every component a callback later updates is declared here up front with its
`id` (the standard Dash pattern) — callbacks only ever set a property on an
existing component, never recreate the component tree.
"""

from __future__ import annotations

import dash_mantine_components as dmc
from dash import dcc

from cca.dashboard.data import MEASURES, OVERALL
from cca.dashboard.faq import GENERAL_FAQ

METHODOLOGY_DRAWER = dmc.Drawer(
    id="methodology-drawer",
    position="right",
    size="md",
    padding="md",
    opened=False,
    title=dmc.Text("Methodology", fw=700),
    children=dmc.Stack(
        gap="md",
        children=[
            *[
                dmc.Stack(
                    gap=4,
                    children=[
                        dmc.Text(question, fw=600, size="sm"),
                        dmc.Text(answer, size="sm", c="dimmed"),
                    ],
                )
                for question, answer in GENERAL_FAQ
            ],
            dmc.Alert(
                "Min-max normalisation pins the lowest district to 0 and the highest to 100 "
                "— the mean sits wherever the distribution's mass is. Averaging several 0–100 "
                "Indicators into a Sector Index also pulls the spread toward the middle.",
                color="gray",
                variant="light",
                title="Why isn't the national average 50?",
            ),
            dmc.Text(
                "The five Sector Indices are never combined into a single composite score (ADR-0002).",
                size="sm",
                fw=500,
            ),
        ],
    ),
)

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


def build_layout(sectors: list[str], *, data_available: bool = True) -> dmc.MantineProvider:
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
          dcc.Store(id="intro-dismissed", storage_type="local"),
          detail_drawer,
          METHODOLOGY_DRAWER,
          dmc.Box(
              id="data-unavailable-banner",
              style={} if not data_available else {"display": "none"},
              children=dmc.Alert(
                  "Data is currently unavailable. Please try again later or contact your administrator.",
                  title="Data unavailable",
                  color="red",
                  variant="filled",
                  m="md",
              ),
          ),
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
                        dmc.Box(
                            id="intro-card-container",
                            mt="sm",
                            mb="sm",
                            children=dmc.Paper(
                                withBorder=True,
                                radius="md",
                                p="sm",
                                style={"backgroundColor": "var(--mantine-color-blue-0)"},
                                children=dmc.Group(
                                    justify="space-between",
                                    align="flex-start",
                                    wrap="nowrap",
                                    children=[
                                        dmc.Stack(
                                            gap=4,
                                            children=[
                                                dmc.Text("Getting started", fw=600, size="sm"),
                                                dmc.Text(
                                                    "Scan the map to spot geographic patterns, "
                                                    "check the ranked list for the most underserved "
                                                    "districts, then click a district to drill into "
                                                    "its Sector breakdown.",
                                                    size="sm",
                                                    c="dimmed",
                                                ),
                                            ],
                                        ),
                                        dmc.ActionIcon(
                                            dmc.Text("✕", size="sm"),
                                            id="dismiss-intro",
                                            variant="subtle",
                                            color="gray",
                                            size="sm",
                                        ),
                                    ],
                                ),
                            ),
                        ),
                        dmc.Grid(
                            gutter="md",
                            mt="md",
                            children=[
                                dmc.GridCol(
                                    span=8,
                                    children=dcc.Loading(
                                        type="circle",
                                        children=dcc.Graph(
                                            id="map-graph",
                                            style={"height": "620px"},
                                            config={"displayModeBar": False},
                                        ),
                                    ),
                                ),
                                dmc.GridCol(
                                    span=4,
                                    children=dcc.Loading(
                                        type="circle",
                                        children=RANKED_LIST_PANEL,
                                    ),
                                ),
                            ],
                        ),
                    ]
                ),
            ],
          ),
        ],
    )
