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
from cca.dashboard.data import build_district_geojson
from cca.dashboard.layout import build_layout
from cca.grid3.client import District
from cca.scoring.indicators import CCA_INDICATORS
from cca.storage.io import read_districts, read_indicator_catalog


def _ordered_sectors() -> list[str]:
    """Sectors in `CCA_indicator_list.csv` order, deduplicated."""
    ordered: list[str] = []
    for meta in CCA_INDICATORS:
        if meta.sector not in ordered:
            ordered.append(meta.sector)
    return ordered


SECTORS = _ordered_sectors()


def build_app(engine: Engine, districts: list[District]) -> Dash:
    districts_df = read_districts(engine)
    geojson = build_district_geojson(districts)
    indicator_catalog = read_indicator_catalog(engine)

    app = Dash(__name__)
    app.layout = build_layout(SECTORS, indicator_catalog)
    register_callbacks(app, engine, districts_df, geojson, SECTORS)
    return app
