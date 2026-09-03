import json

import pytest

from cca.grid3.client import (
    District,
    fetch_district_master_list,
    parse_feature_collection,
    read_simplified_district_boundaries,
    write_simplified_boundary_cache,
)

DISTRICT_COUNT = 116


def _sample_geojson(n: int = DISTRICT_COUNT) -> dict:
    """Build a GRID3-shaped FeatureCollection fixture — never the live endpoint."""
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
                    "coordinates": [[[28.0 + i, -15.0], [28.1 + i, -15.0], [28.1 + i, -15.1]]],
                },
            }
            for i in range(n)
        ],
    }


class TestParseFeatureCollection:
    def test_parses_the_full_expected_116_district_cohort(self):
        districts = parse_feature_collection(_sample_geojson())
        assert len(districts) == DISTRICT_COUNT
        assert all(isinstance(d, District) for d in districts)

    def test_extracts_name_code_province_and_geometry_per_district(self):
        districts = parse_feature_collection(_sample_geojson(n=1))
        district = districts[0]
        assert district.name == "District 0"
        assert district.code == "D000"
        assert district.province == "Province 0"
        assert district.province_code == "P00"
        assert district.geometry["type"] == "Polygon"


class TestFetchDistrictMasterList:
    def test_fetches_and_writes_the_cache_when_none_exists(self, tmp_path):
        cache_path = tmp_path / "grid3_districts.json"
        calls = []

        def fetch_geojson():
            calls.append(1)
            return _sample_geojson()

        districts = fetch_district_master_list(cache_path, fetch_geojson=fetch_geojson)

        assert len(districts) == DISTRICT_COUNT
        assert len(calls) == 1
        assert cache_path.exists()
        assert json.loads(cache_path.read_text())["features"][0]["properties"]["DISTRICT"] == "District 0"

    def test_reuses_the_cache_without_refetching_within_a_refresh_cycle(self, tmp_path):
        cache_path = tmp_path / "grid3_districts.json"
        cache_path.write_text(json.dumps(_sample_geojson()))
        calls = []

        def fetch_geojson():
            calls.append(1)
            return _sample_geojson()

        districts = fetch_district_master_list(cache_path, fetch_geojson=fetch_geojson)

        assert len(districts) == DISTRICT_COUNT
        assert calls == []

    def test_force_refresh_refetches_and_overwrites_an_existing_cache(self, tmp_path):
        cache_path = tmp_path / "grid3_districts.json"
        cache_path.write_text(json.dumps(_sample_geojson(n=1)))
        calls = []

        def fetch_geojson():
            calls.append(1)
            return _sample_geojson(n=DISTRICT_COUNT)

        districts = fetch_district_master_list(
            cache_path, force_refresh=True, fetch_geojson=fetch_geojson
        )

        assert len(districts) == DISTRICT_COUNT
        assert len(calls) == 1
        assert len(json.loads(cache_path.read_text())["features"]) == DISTRICT_COUNT

    def test_a_malformed_refetch_does_not_clobber_the_last_known_good_cache(self, tmp_path):
        cache_path = tmp_path / "grid3_districts.json"
        good_geojson = _sample_geojson()
        cache_path.write_text(json.dumps(good_geojson))

        def fetch_malformed_geojson():
            return {"type": "FeatureCollection", "features": [{"properties": {}, "geometry": {}}]}

        with pytest.raises(KeyError):
            fetch_district_master_list(
                cache_path, force_refresh=True, fetch_geojson=fetch_malformed_geojson
            )

        assert json.loads(cache_path.read_text()) == good_geojson


class TestDistrictHashing:
    def test_districts_are_hashable_despite_the_geometry_dict_field(self):
        district = parse_feature_collection(_sample_geojson(n=1))[0]
        assert {district} == {district}


class TestSimplifiedBoundaryCache:
    def test_write_then_read_round_trips_identity_fields_and_geometry(self, tmp_path):
        districts = parse_feature_collection(_sample_geojson(n=3))
        cache_path = tmp_path / "grid3_districts_simplified.json"

        write_simplified_boundary_cache(districts, cache_path)
        read_back = read_simplified_district_boundaries(cache_path)

        assert len(read_back) == 3
        assert {d.code for d in read_back} == {d.code for d in districts}
        by_code = {d.code: d for d in read_back}
        assert by_code["D000"].name == "District 0"
        assert by_code["D000"].province == "Province 0"
        assert by_code["D000"].geometry == districts[0].geometry

    def test_write_creates_missing_parent_directories(self, tmp_path):
        districts = parse_feature_collection(_sample_geojson(n=1))
        cache_path = tmp_path / "nested" / "dir" / "grid3_districts_simplified.json"

        write_simplified_boundary_cache(districts, cache_path)

        assert cache_path.exists()
