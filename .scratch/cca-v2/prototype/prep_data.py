"""PROTOTYPE — throwaway. Prepares light data for the v2 layout prototype.

Reads the full-resolution GRID3 district cache, simplifies each district
polygon with shapely (Douglas-Peucker, topology-preserving) and rounds
coordinates, then writes:
  - districts_simplified.geojson  (id = str(DIST_CODE), props: name, province)
  - districts.json                (code/name/province/is_urban master list)

This is the build-time geometry-simplification step the v2 spec calls for,
done once here so the prototype loads a small payload instead of 32.9 MB.
"""

from __future__ import annotations

import json
import os

from shapely.geometry import mapping, shape

HERE = os.path.dirname(__file__)
CACHE = os.path.join(HERE, "..", "..", "..", "scripts", ".grid3_districts_cache.json")
SIMPLIFY_TOLERANCE = 0.005  # degrees (~500 m); shape stays legible, vertices plummet
COORD_DECIMALS = 4

# A handful of well-known mostly-urban districts, for the Urban-chip demo.
URBAN_NAMES = {"Lusaka", "Ndola", "Kitwe", "Livingstone", "Kabwe", "Chingola"}


def _round_geojson(obj):
    if isinstance(obj, float):
        return round(obj, COORD_DECIMALS)
    if isinstance(obj, list):
        return [_round_geojson(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _round_geojson(v) for k, v in obj.items()}
    return obj


def main() -> None:
    with open(CACHE, encoding="utf-8") as f:
        raw = json.load(f)

    features = []
    districts = []
    total_vertices = 0
    for feat in raw["features"]:
        props = feat["properties"]
        code = str(props["DIST_CODE"])
        name = props["DISTRICT"]
        province = props["PROVINCE"]

        geom = shape(feat["geometry"]).simplify(SIMPLIFY_TOLERANCE, preserve_topology=True)
        gj = _round_geojson(mapping(geom))
        total_vertices += sum(len(ring) for ring in gj["coordinates"])

        features.append(
            {
                "type": "Feature",
                "id": code,
                "properties": {"name": name, "province": province},
                "geometry": gj,
            }
        )
        districts.append(
            {
                "code": code,
                "name": name,
                "province": province,
                "is_urban": name in URBAN_NAMES,
            }
        )

    fc = {"type": "FeatureCollection", "features": features}
    geo_path = os.path.join(HERE, "districts_simplified.geojson")
    dist_path = os.path.join(HERE, "districts.json")
    with open(geo_path, "w", encoding="utf-8") as f:
        json.dump(fc, f)
    with open(dist_path, "w", encoding="utf-8") as f:
        json.dump(districts, f, indent=2)

    size_kb = os.path.getsize(geo_path) / 1024
    print(f"districts: {len(districts)}")
    print(f"total vertices after simplify: {total_vertices:,}")
    print(f"districts_simplified.geojson: {size_kb:,.1f} KB")


if __name__ == "__main__":
    main()
