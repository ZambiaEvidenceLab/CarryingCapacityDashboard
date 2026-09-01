import pytest

from cca.grid3.client import District
from cca.scoring.engine import IndicatorMeta, run_scoring
from cca.scoring.indicators import CCA_INDICATORS
from cca.synthetic.generator import generate_synthetic_dataset, generate_synthetic_indicators

DISTRICT_COUNT = 116
DISTRICT_CODES = [f"D{i:03d}" for i in range(DISTRICT_COUNT)]


def _sample_districts(n: int = DISTRICT_COUNT) -> list[District]:
    """Build GRID3-shaped District fixtures — never the live endpoint."""
    return [
        District(
            name=f"District {i}",
            code=f"D{i:03d}",
            province=f"Province {i % 10}",
            province_code=f"P{i % 10:02d}",
            geometry={"type": "Polygon", "coordinates": []},
        )
        for i in range(n)
    ]


class TestGenerateSyntheticIndicators:
    def test_output_columns_match_the_scoring_engines_input_format(self):
        raw = generate_synthetic_indicators(DISTRICT_CODES, CCA_INDICATORS, seed=1)
        assert list(raw.columns) == ["district_code", "indicator_id", "value"]

    def test_covers_all_districts_and_all_indicators_with_no_missing_data(self):
        raw = generate_synthetic_indicators(DISTRICT_CODES, CCA_INDICATORS, seed=1, missing_rate=0)
        assert set(raw["district_code"]) == set(DISTRICT_CODES)
        assert set(raw["indicator_id"]) == {m.indicator_id for m in CCA_INDICATORS}
        assert len(raw) == DISTRICT_COUNT * len(CCA_INDICATORS)

    def test_rejects_an_indicator_with_no_defined_synthetic_range(self):
        meta = [IndicatorMeta("unknown_indicator", "Health", "Supply")]
        with pytest.raises(ValueError, match="unknown_indicator"):
            generate_synthetic_indicators(DISTRICT_CODES, meta, seed=1)


class TestGenerateSyntheticDataset:
    def test_uses_real_district_codes_from_the_grid3_client_and_the_canonical_cca_indicator_catalog(self):
        districts = _sample_districts()
        raw = generate_synthetic_dataset(districts, seed=1, missing_rate=0)
        assert set(raw["district_code"]) == {d.code for d in districts}
        assert set(raw["indicator_id"]) == {m.indicator_id for m in CCA_INDICATORS}


class TestSyntheticDataFeedsThroughTheScoringEngine:
    def test_produces_valid_sector_index_scores_without_errors(self):
        districts = _sample_districts()
        district_codes = [d.code for d in districts]
        raw = generate_synthetic_dataset(districts, seed=42)

        result = run_scoring(raw, CCA_INDICATORS, district_codes)

        assert result.validation.passed, result.validation.reasons
        assert set(result.sector_scores["district_code"]) == set(district_codes)
        assert set(result.sector_scores["sector"]) == {
            "Health", "Education", "Agriculture", "Infrastructure", "Environment",
        }
        assert result.sector_scores["score"].notna().all()

    def test_deliberately_missing_values_produce_some_incomplete_sector_scores(self):
        districts = _sample_districts()
        district_codes = [d.code for d in districts]
        raw = generate_synthetic_dataset(districts, seed=42, missing_rate=0.2)

        result = run_scoring(raw, CCA_INDICATORS, district_codes)

        assert result.validation.passed, result.validation.reasons
        assert (~result.sector_scores["complete"]).any()

    def test_deliberate_outliers_trigger_winsorization_capping(self):
        districts = _sample_districts()
        district_codes = [d.code for d in districts]
        raw = generate_synthetic_dataset(districts, seed=42, outlier_rate=0.1)

        result = run_scoring(raw, CCA_INDICATORS, district_codes)

        assert result.validation.passed, result.validation.reasons
        capped = [
            report.indicator_id
            for report in result.winsorization_reports.values()
            if report.capped_districts
        ]
        assert capped
