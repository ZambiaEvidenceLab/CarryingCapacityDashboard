"""GRID3 client — fetches Zambia's 116-district master list (ADR-0006).

Unlike the scoring engine, this is an adapter: it makes a network call and
writes a local cache. GRID3 is only queried at a data-refresh cycle, not on
every dashboard page load, so a GRID3 outage doesn't take the dashboard
down. Tests exercise it against a cached fixture, never the live endpoint.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests

# The GRID3 NSDI_Zambia_Districts_2022 layer — see ADR-0006 for provenance.
FEATURESERVER_URL = (
    "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/"
    "Zambia_Administrative_Boundaries_Districts_2020/FeatureServer/0/query"
    "?where=1=1&outFields=*&f=geojson"
)


@dataclass(frozen=True)
class District:
    name: str
    code: str
    province: str
    province_code: str
    geometry: dict

    def __hash__(self) -> int:
        # geometry is a dict (unhashable) — identify a District by its
        # administrative fields instead so it can still go in a set/dict key.
        return hash((self.name, self.code, self.province, self.province_code))


def parse_feature_collection(geojson: dict) -> list[District]:
    """Parse a GRID3 GeoJSON FeatureCollection into District records."""
    return [
        District(
            name=feature["properties"]["DISTRICT"],
            code=feature["properties"]["DIST_CODE"],
            province=feature["properties"]["PROVINCE"],
            province_code=feature["properties"]["PROV_CODE"],
            geometry=feature["geometry"],
        )
        for feature in geojson["features"]
    ]


def _to_feature_collection(districts: list[District]) -> dict:
    """The GRID3-shaped GeoJSON FeatureCollection form of `districts` (round-trips via `parse_feature_collection`)."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "DISTRICT": d.name,
                    "DIST_CODE": d.code,
                    "PROVINCE": d.province,
                    "PROV_CODE": d.province_code,
                },
                "geometry": d.geometry,
            }
            for d in districts
        ],
    }


def _fetch_geojson_from_grid3() -> dict:
    response = requests.get(FEATURESERVER_URL, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_district_master_list(
    cache_path: str | Path,
    *,
    force_refresh: bool = False,
    fetch_geojson: Callable[[], dict] = _fetch_geojson_from_grid3,
) -> list[District]:
    """Return the 116-district master list, using the local cache unless refreshing.

    Per ADR-0006, callers pass `force_refresh=True` at a data-refresh cycle to
    hit GRID3 and repopulate the cache; otherwise an existing cache is reused
    so a GRID3 outage doesn't take the dashboard down.
    """
    cache_path = Path(cache_path)

    if cache_path.exists() and not force_refresh:
        geojson = json.loads(cache_path.read_text())
        return parse_feature_collection(geojson)

    geojson = fetch_geojson()
    # Parse before writing the cache — a malformed/schema-drifted response
    # must not clobber the last-known-good cache that ADR-0006 relies on to
    # survive a GRID3 outage.
    districts = parse_feature_collection(geojson)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(geojson))
    return districts


def write_simplified_boundary_cache(districts: list[District], cache_path: str | Path) -> None:
    """Write `districts` (already simplified) to their own cache file, alongside
    the full-resolution GRID3 cache (ADR-0017)."""
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(_to_feature_collection(districts)))


def read_simplified_district_boundaries(cache_path: str | Path) -> list[District]:
    """Read the simplified boundary set the dashboard renders the map from."""
    return parse_feature_collection(json.loads(Path(cache_path).read_text()))
