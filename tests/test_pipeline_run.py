from datetime import datetime, timezone

import pandas as pd
import pytest
from sqlalchemy import text

from cca.grid3.client import District
from cca.pipeline.run import run_validation_and_publish
from cca.scoring.engine import IndicatorMeta
from cca.storage.io import write_district_master_list

SUBMITTED_AT = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

DISTRICTS = [
    District(code="D001", name="Lusaka", province="Lusaka", province_code="P01", geometry={}),
    District(code="D002", name="Ndola", province="Copperbelt", province_code="P02", geometry={}),
]

INDICATOR_METAS = [
    IndicatorMeta("health_doctor_to_population_ratio", "Health", "Supply"),
    IndicatorMeta("environment_forest_cover", "Environment", None),
]


@pytest.fixture
def pg(clean_pg):
    write_district_master_list(clean_pg, DISTRICTS)
    return clean_pg


def _write_csv(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


class TestRunValidationAndPublishSuccess:
    def test_a_fully_passing_submission_is_published_and_scored(self, pg, tmp_path):
        source = _write_csv(
            tmp_path / "incoming.csv",
            [
                {"district_name": "Lusaka", "indicator_id": "health_doctor_to_population_ratio", "value": 0.2},
                {"district_name": "Ndola", "indicator_id": "health_doctor_to_population_ratio", "value": 0.3},
                {"district_name": "Lusaka", "indicator_id": "environment_forest_cover", "value": 40.0},
                {"district_name": "Ndola", "indicator_id": "environment_forest_cover", "value": 60.0},
            ],
        )

        result = run_validation_and_publish(
            pg,
            source,
            sector="Health",
            submitter="mofnp",
            districts=DISTRICTS,
            indicator_metas=INDICATOR_METAS,
            data_lake_root=tmp_path / "data" / "raw",
            reports_root=tmp_path / "docs" / "validation-reports",
            submitted_at=SUBMITTED_AT,
        )

        assert result.status == "published"
        assert result.validation.passed
        assert result.run_id is not None

        with pg.connect() as conn:
            row = conn.execute(
                text("SELECT status, validation_report_path FROM catalog.submissions WHERE submission_id = :id"),
                {"id": result.submission_id},
            ).mappings().one()
        assert row["status"] == "published"
        assert row["validation_report_path"] == result.report_path

        with pg.connect() as conn:
            scores = pd.read_sql(text("SELECT * FROM indices.scores WHERE dimension IS NULL"), conn)
        assert len(scores) == 4  # 2 districts x 2 sectors

    def test_the_raw_file_is_stored_and_never_deleted(self, pg, tmp_path):
        source = _write_csv(
            tmp_path / "incoming.csv",
            [{"district_name": "Lusaka", "indicator_id": "environment_forest_cover", "value": 40.0},
             {"district_name": "Ndola", "indicator_id": "environment_forest_cover", "value": 60.0}],
        )
        data_lake_root = tmp_path / "data" / "raw"

        run_validation_and_publish(
            pg, source, sector="Environment", submitter="mofnp", districts=DISTRICTS,
            indicator_metas=[IndicatorMeta("environment_forest_cover", "Environment", None)],
            data_lake_root=data_lake_root, reports_root=tmp_path / "docs" / "validation-reports",
            submitted_at=SUBMITTED_AT,
        )

        stored_files = list((data_lake_root / "environment").glob("*.csv"))
        assert len(stored_files) == 1
        assert stored_files[0].read_text() == source.read_text()


class TestDefaultIndicatorScoping:
    def test_an_unscoped_submission_only_scores_the_indicators_it_actually_contains(self, pg, tmp_path):
        """Regression: run_scoring must not be called against the full multi-sector

        catalog when a submission only covers one sector's indicators -- doing
        so would write incomplete=True/score=None rows for every other sector
        into the new current run, silently blanking their still-valid published
        scores (schema.py's `runs` table has exactly one global current run).
        """
        source = _write_csv(
            tmp_path / "incoming.csv",
            [{"district_name": "Lusaka", "indicator_id": "environment_forest_cover", "value": 40.0},
             {"district_name": "Ndola", "indicator_id": "environment_forest_cover", "value": 60.0}],
        )

        result = run_validation_and_publish(
            pg, source, sector="Environment", submitter="mofnp", districts=DISTRICTS,
            data_lake_root=tmp_path / "data" / "raw", reports_root=tmp_path / "docs" / "validation-reports",
            submitted_at=SUBMITTED_AT,
        )

        assert result.status == "published"
        with pg.connect() as conn:
            scores = pd.read_sql(text("SELECT sector FROM indices.scores WHERE dimension IS NULL"), conn)
        assert set(scores["sector"]) == {"Environment"}


class TestRunValidationAndPublishRejection:
    def test_an_unknown_district_name_is_rejected_and_the_raw_file_is_kept(self, pg, tmp_path):
        source = _write_csv(
            tmp_path / "incoming.csv",
            [{"district_name": "Atlantis", "indicator_id": "environment_forest_cover", "value": 40.0}],
        )
        data_lake_root = tmp_path / "data" / "raw"

        result = run_validation_and_publish(
            pg, source, sector="Environment", submitter="mofnp", districts=DISTRICTS,
            indicator_metas=[IndicatorMeta("environment_forest_cover", "Environment", None)],
            data_lake_root=data_lake_root, reports_root=tmp_path / "docs" / "validation-reports",
            submitted_at=SUBMITTED_AT,
        )

        assert result.status == "rejected"
        assert not result.validation.passed
        assert result.run_id is None
        assert any("Atlantis" in reason for reason in result.validation.reasons)

        with pg.connect() as conn:
            status = conn.execute(
                text("SELECT status FROM catalog.submissions WHERE submission_id = :id"),
                {"id": result.submission_id},
            ).scalar_one()
        assert status == "rejected"
        assert list((data_lake_root / "environment").glob("*.csv"))

    def test_an_out_of_range_value_is_rejected(self, pg, tmp_path):
        source = _write_csv(
            tmp_path / "incoming.csv",
            [{"district_name": "Lusaka", "indicator_id": "health_doctor_to_population_ratio", "value": 999.0},
             {"district_name": "Ndola", "indicator_id": "health_doctor_to_population_ratio", "value": 0.3}],
        )

        result = run_validation_and_publish(
            pg, source, sector="Health", submitter="mofnp", districts=DISTRICTS,
            indicator_metas=[IndicatorMeta("health_doctor_to_population_ratio", "Health", "Supply")],
            data_lake_root=tmp_path / "data" / "raw", reports_root=tmp_path / "docs" / "validation-reports",
            submitted_at=SUBMITTED_AT,
        )

        assert result.status == "rejected"
        assert result.run_id is None
