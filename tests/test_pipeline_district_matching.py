import pandas as pd
import pytest

from cca.grid3.client import District
from cca.pipeline.district_matching import match_district_names

DISTRICTS = [
    District(code="D001", name="Lusaka", province="Lusaka", province_code="P01", geometry={}),
    District(code="D002", name="Ndola", province="Copperbelt", province_code="P02", geometry={}),
]


def _rows(*pairs):
    return pd.DataFrame(
        [{"district_name": name, "indicator_id": "health_doctor_to_population_ratio", "value": 1.0} for name in pairs]
    )


class TestMatchDistrictNames:
    def test_maps_known_names_to_their_district_codes(self):
        mapped, result = match_district_names(_rows("Lusaka", "Ndola"), DISTRICTS)

        assert result.passed
        assert sorted(mapped["district_code"]) == ["D001", "D002"]
        assert "district_name" not in mapped.columns

    def test_is_case_and_whitespace_insensitive(self):
        mapped, result = match_district_names(_rows(" lusaka ", "NDOLA"), DISTRICTS)

        assert result.passed
        assert sorted(mapped["district_code"]) == ["D001", "D002"]

    def test_rejects_a_name_not_in_the_master_list(self):
        mapped, result = match_district_names(_rows("Lusaka", "Atlantis"), DISTRICTS)

        assert not result.passed
        assert any("Atlantis" in reason for reason in result.reasons)
        # Only the matched row survives into the mapped output.
        assert list(mapped["district_code"]) == ["D001"]

    def test_empty_input_matches_trivially(self):
        mapped, result = match_district_names(pd.DataFrame(columns=["district_name", "indicator_id", "value"]), DISTRICTS)

        assert result.passed
        assert mapped.empty
