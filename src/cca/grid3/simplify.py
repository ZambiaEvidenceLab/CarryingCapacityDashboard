"""Build/refresh-time boundary simplification (ADR-0017).

The full-resolution GRID3 geometry is ~32.9 MB / ~847k vertices — far too
much to ship to the browser on every dashboard load. This module reduces it
to the order of ~15k vertices while keeping every district's shape legible,
using topology-preserving Douglas-Peucker simplification. It is only ever
called from a data-refresh script (see `cca.grid3.client`), never from the
running dashboard (ADR-0010).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from shapely.geometry import mapping, shape

from cca.grid3.client import (
    District,
    read_simplified_district_boundaries,
    write_simplified_boundary_cache,
)

# Degrees (~500 m at Zambia's latitude) — the prototype's tolerance, which
# took the full-resolution set to ~13k vertices / 512 KB while keeping every
# district shape legible at national zoom (`.scratch/cca-v2/prototype/prep_data.py`).
SIMPLIFY_TOLERANCE = 0.005
COORD_DECIMALS = 4


def _round_coordinates(value, decimals: int):
    if isinstance(value, float):
        return round(value, decimals)
    if isinstance(value, (list, tuple)):
        return [_round_coordinates(item, decimals) for item in value]
    return value


def simplify_geometry(geometry: dict, *, tolerance: float, decimals: int) -> dict:
    """Simplify one GeoJSON geometry, preserving topology, and round its coordinates."""
    simplified = shape(geometry).simplify(tolerance, preserve_topology=True)
    geojson = mapping(simplified)
    return {**geojson, "coordinates": _round_coordinates(geojson["coordinates"], decimals)}


def simplify_districts(
    districts: list[District],
    *,
    tolerance: float = SIMPLIFY_TOLERANCE,
    decimals: int = COORD_DECIMALS,
) -> list[District]:
    """Return `districts` with simplified geometry; all other fields are unchanged.

    Retains every district — simplification only reduces vertex density, it
    never drops a district or alters its name/code/province.
    """
    return [
        replace(d, geometry=simplify_geometry(d.geometry, tolerance=tolerance, decimals=decimals))
        for d in districts
    ]


def ensure_simplified_boundary_cache(
    districts: list[District],
    cache_path: str | Path,
    *,
    force_refresh: bool = False,
    tolerance: float = SIMPLIFY_TOLERANCE,
) -> list[District]:
    """Return the simplified boundary set, computing and caching it only once per refresh.

    Simplification is a data-refresh-time step (ADR-0017), not a page-load
    one: if `cache_path` already holds a simplified set and no refresh is
    requested, it's read back directly rather than re-simplified.
    """
    cache_path = Path(cache_path)
    if cache_path.exists() and not force_refresh:
        return read_simplified_district_boundaries(cache_path)

    simplified = simplify_districts(districts, tolerance=tolerance)
    write_simplified_boundary_cache(simplified, cache_path)
    return simplified
