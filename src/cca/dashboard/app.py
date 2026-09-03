"""Dash app factory for the CCA dashboard (ADR-0005).

Performs no calculation at runtime (ADR-0010) — everything here reads the
processed Postgres layer and the cached GRID3 boundaries, then reshapes rows
for display. Callers (see `scripts/run_dashboard.py`) supply an `Engine` and
the GRID3 district list; this module has no opinion on connection strings or
where the GRID3 cache file lives.
"""

from __future__ import annotations

from dash import Dash
from sqlalchemy import Engine

from cca.dashboard.callbacks import register_callbacks
from cca.dashboard.data import build_district_geojson, build_district_points
from cca.dashboard.layout import build_layout
from cca.grid3.client import District
from cca.scoring.indicators import CCA_INDICATORS
from cca.storage.io import read_districts


def _ordered_sectors() -> list[str]:
    """Sectors in `CCA_indicator_list.csv` order, deduplicated."""
    ordered: list[str] = []
    for meta in CCA_INDICATORS:
        if meta.sector not in ordered:
            ordered.append(meta.sector)
    return ordered


SECTORS = _ordered_sectors()


# Ranked-list rows carry an `all:unset` reset (they're semantic <button>s, not
# styled boxes) plus a hover and a selected accent. Injected once at build time.
_ROW_CSS = """<style>
  .rank-row{all:unset;cursor:pointer;display:block;width:100%;padding:6px 8px;border-radius:8px;box-sizing:border-box;}
  .rank-row:hover{background:#F1F5F5;}
  .rank-row--selected{background:#EAF1F1;}
</style></head>"""


def build_app(engine: Engine, districts: list[District]) -> Dash:
    districts_df = read_districts(engine)
    geojson = build_district_geojson(districts)
    district_points = build_district_points(districts)

    # Ranked-list rows are created inside a callback, not the static layout, so
    # their pattern-matching `n_clicks` Inputs aren't present at startup.
    app = Dash(__name__, suppress_callback_exceptions=True)
    app.index_string = app.index_string.replace("</head>", _ROW_CSS)
    app.layout = build_layout(SECTORS)
    register_callbacks(app, engine, districts_df, geojson, district_points)
    return app
