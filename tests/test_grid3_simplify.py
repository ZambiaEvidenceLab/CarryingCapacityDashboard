from cca.grid3.client import (
    District,
    parse_feature_collection,
    read_simplified_district_boundaries,
    write_simplified_boundary_cache,
)
from cca.grid3.simplify import ensure_simplified_boundary_cache, simplify_districts

DISTRICT_COUNT = 116


def _sample_geojson(n: int = DISTRICT_COUNT) -> dict:
    """Build a GRID3-shaped FeatureCollection fixture."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "DISTRICT": f"District {i}",
                    "DIST_CODE": f"D{i:03d}",
                    "PROVINCE": f"Province {i % 10}",
                    "PROV_CODE": f"P{i % 10:02d}",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[28.0 + i, -15.0], [28.1 + i, -15.0], [28.1 + i, -15.1], [28.0 + i, -15.0]]],
                },
            }
            for i in range(n)
        ],
    }

# A near-circular 65-point polygon (well above what 0.02 tolerance needs to
# keep it a legible square) so simplification has real vertices to drop.
_MANY_VERTICES = [[round(28.0 + 0.001 * i, 6), round(-15.0 + 0.0005 * i, 6)] for i in range(64)]
_MANY_VERTICES.append(_MANY_VERTICES[0])

DISTRICTS = [
    District(
        name="D1 Town",
        code="D1",
        province="P1",
        province_code="PC1",
        geometry={"type": "Polygon", "coordinates": [_MANY_VERTICES]},
    ),
    District(
        name="D2 City",
        code="D2",
        province="P2",
        province_code="PC2",
        geometry={"type": "Polygon", "coordinates": [_MANY_VERTICES]},
    ),
]


class TestSimplifyDistricts:
    def test_retains_every_district_by_code(self):
        simplified = simplify_districts(DISTRICTS, tolerance=0.02)

        assert {d.code for d in simplified} == {"D1", "D2"}

    def test_preserves_identity_fields_unchanged(self):
        simplified = simplify_districts(DISTRICTS, tolerance=0.02)
        by_code = {d.code: d for d in simplified}

        assert by_code["D1"].name == "D1 Town"
        assert by_code["D1"].province == "P1"
        assert by_code["D1"].province_code == "PC1"

    def test_reduces_vertex_count(self):
        simplified = simplify_districts(DISTRICTS, tolerance=0.02)

        original_vertices = len(DISTRICTS[0].geometry["coordinates"][0])
        simplified_vertices = len(simplified[0].geometry["coordinates"][0])
        assert simplified_vertices < original_vertices

    def test_rounds_coordinates_to_the_given_precision(self):
        simplified = simplify_districts(DISTRICTS, tolerance=0.02, decimals=2)

        for ring in simplified[0].geometry["coordinates"]:
            for lon, lat in ring:
                assert lon == round(lon, 2)
                assert lat == round(lat, 2)

    def test_a_tiny_tolerance_still_preserves_polygon_topology(self):
        simplified = simplify_districts(DISTRICTS, tolerance=1e-9)

        assert simplified[0].geometry["type"] == "Polygon"


class TestEnsureSimplifiedBoundaryCache:
    def test_simplifies_and_writes_the_cache_when_none_exists(self, tmp_path):
        districts = parse_feature_collection(_sample_geojson())
        cache_path = tmp_path / "grid3_districts_simplified.json"

        simplified = ensure_simplified_boundary_cache(districts, cache_path, tolerance=0.02)

        assert len(simplified) == DISTRICT_COUNT
        assert cache_path.exists()

    def test_reuses_the_cache_without_re_simplifying_when_it_already_exists(self, tmp_path, monkeypatch):
        districts = parse_feature_collection(_sample_geojson())
        cache_path = tmp_path / "grid3_districts_simplified.json"
        ensure_simplified_boundary_cache(districts, cache_path, tolerance=0.02)

        import cca.grid3.simplify as simplify_module

        def _boom(*args, **kwargs):
            raise AssertionError("should not re-simplify when a cache already exists")

        monkeypatch.setattr(simplify_module, "simplify_districts", _boom)

        simplified = ensure_simplified_boundary_cache(districts, cache_path, tolerance=0.02)

        assert len(simplified) == DISTRICT_COUNT

    def test_force_refresh_re_simplifies_and_overwrites_an_existing_cache(self, tmp_path):
        cache_path = tmp_path / "grid3_districts_simplified.json"
        write_simplified_boundary_cache(parse_feature_collection(_sample_geojson(n=1)), cache_path)

        districts = parse_feature_collection(_sample_geojson())
        simplified = ensure_simplified_boundary_cache(
            districts, cache_path, force_refresh=True, tolerance=0.02
        )

        assert len(simplified) == DISTRICT_COUNT
        assert len(read_simplified_district_boundaries(cache_path)) == DISTRICT_COUNT

    def test_retains_all_116_districts_and_drops_vertices(self, tmp_path):
        # Real-shaped many-vertex polygon so simplification has something to reduce.
        many_vertices = [[28.0 + 0.0005 * i, -15.0 + 0.0002 * i] for i in range(80)]
        many_vertices.append(many_vertices[0])
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "DISTRICT": f"District {i}",
                        "DIST_CODE": f"D{i:03d}",
                        "PROVINCE": f"Province {i % 10}",
                        "PROV_CODE": f"P{i % 10:02d}",
                    },
                    "geometry": {"type": "Polygon", "coordinates": [many_vertices]},
                }
                for i in range(DISTRICT_COUNT)
            ],
        }
        districts = parse_feature_collection(geojson)
        cache_path = tmp_path / "grid3_districts_simplified.json"

        simplified = ensure_simplified_boundary_cache(districts, cache_path, tolerance=0.01)

        assert len(simplified) == DISTRICT_COUNT
        assert {d.code for d in simplified} == {d.code for d in districts}
        assert len(simplified[0].geometry["coordinates"][0]) < len(many_vertices)
