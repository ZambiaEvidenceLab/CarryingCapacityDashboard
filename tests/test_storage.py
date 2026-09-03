import pandas as pd
import pytest
from sqlalchemy import inspect, text

from cca.grid3.client import District
from cca.scoring.engine import IndicatorMeta, run_scoring
from cca.storage.io import (
    read_district_decomposition,
    read_districts,
    read_indicator_cohort_values,
    read_latest_sector_scores,
    read_national_summary,
    read_sector_cohort_values,
    update_submission_status,
    write_district_master_list,
    write_indicator_metadata,
    write_scoring_run,
    write_submission,
)

DISTRICTS = ["D1", "D2", "D3"]

DISTRICT_RECORDS = [
    District(code="D1", name="D1 Town", province="P1", province_code="PC1", geometry={}),
    District(code="D2", name="D2 Town", province="P1", province_code="PC1", geometry={}),
    District(code="D3", name="D3 City", province="P2", province_code="PC2", geometry={}),
]

INDICATOR_METAS = [
    IndicatorMeta("health_doctor_to_population_ratio", "Health", "Supply"),
    IndicatorMeta("health_distance_to_nearest_facility", "Health", "Access", "invert"),
    IndicatorMeta("environment_forest_cover", "Environment", None),
]


@pytest.fixture
def pg(clean_pg):
    """A `clean_pg` with the GRID3 district master list already seeded.

    Required before writing scores/indicator values -- both are
    foreign-keyed to `metadata.districts`.
    """
    write_district_master_list(clean_pg, DISTRICT_RECORDS, urban_district_names=frozenset({"D3 City"}))
    return clean_pg


def _raw_values() -> pd.DataFrame:
    rows = [
        {"district_code": "D1", "indicator_id": "health_doctor_to_population_ratio", "value": 0.1},
        {"district_code": "D2", "indicator_id": "health_doctor_to_population_ratio", "value": 0.3},
        {"district_code": "D3", "indicator_id": "health_doctor_to_population_ratio", "value": 0.5},
        {"district_code": "D1", "indicator_id": "health_distance_to_nearest_facility", "value": 20.0},
        {"district_code": "D2", "indicator_id": "health_distance_to_nearest_facility", "value": 10.0},
        # D3's health_distance_to_nearest_facility is deliberately missing.
        {"district_code": "D1", "indicator_id": "environment_forest_cover", "value": 40.0},
        {"district_code": "D2", "indicator_id": "environment_forest_cover", "value": 60.0},
        {"district_code": "D3", "indicator_id": "environment_forest_cover", "value": 80.0},
    ]
    return pd.DataFrame(rows)


def _run():
    return run_scoring(_raw_values(), INDICATOR_METAS, DISTRICTS)


class TestCreateAll:
    def test_creates_the_expected_schemas_and_tables(self, clean_pg):
        inspector = inspect(clean_pg)
        for schema, table in [
            ("indices", "runs"),
            ("indices", "scores"),
            ("indicators", "indicator_values"),
            ("metadata", "indicator_definitions"),
            ("metadata", "districts"),
            ("catalog", "submissions"),
        ]:
            assert inspector.has_table(table, schema=schema)


class TestWriteScoringRun:
    def test_round_trips_sector_scores_through_a_write_and_read(self, pg):
        result = _run()

        write_scoring_run(pg, result, INDICATOR_METAS)
        read_back = read_latest_sector_scores(pg).sort_values(["district_code", "sector"]).reset_index(drop=True)

        expected = result.sector_scores.sort_values(["district_code", "sector"]).reset_index(drop=True)
        pd.testing.assert_frame_equal(read_back, expected, check_dtype=False)

    def test_round_trips_dimension_scores_through_a_write_and_read(self, pg):
        result = _run()

        write_scoring_run(pg, result, INDICATOR_METAS)
        with pg.connect() as conn:
            stored = pd.read_sql(
                text(
                    "SELECT district_code, sector, dimension, score, complete, n_used, n_total "
                    "FROM indices.scores WHERE dimension IS NOT NULL"
                ),
                conn,
            )

        sort_cols = ["district_code", "sector", "dimension"]
        stored = stored.sort_values(sort_cols).reset_index(drop=True)
        expected = result.dimension_scores.sort_values(sort_cols).reset_index(drop=True)[stored.columns]
        pd.testing.assert_frame_equal(stored, expected, check_dtype=False)

    def test_round_trips_normalised_indicator_values_through_a_write_and_read(self, pg):
        result = _run()

        write_scoring_run(pg, result, INDICATOR_METAS)
        with pg.connect() as conn:
            stored = pd.read_sql(
                text("SELECT district_code, indicator_id, value FROM indicators.indicator_values"), conn
            ).sort_values(["district_code", "indicator_id"]).reset_index(drop=True)

        expected_records = [
            {"district_code": district_code, "indicator_id": indicator_id, "value": float(value)}
            for indicator_id, indicator_score in result.indicator_scores.items()
            for district_code, value in indicator_score.normalised.items()
            if pd.notna(value)
        ]
        expected = pd.DataFrame(expected_records).sort_values(["district_code", "indicator_id"]).reset_index(drop=True)
        pd.testing.assert_frame_equal(stored, expected, check_dtype=False)

    def test_round_trips_raw_indicator_values_alongside_the_normalised_ones(self, pg):
        result = _run()

        write_scoring_run(pg, result, INDICATOR_METAS)
        with pg.connect() as conn:
            stored = pd.read_sql(
                text("SELECT district_code, indicator_id, raw_value FROM indicators.indicator_values"), conn
            ).sort_values(["district_code", "indicator_id"]).reset_index(drop=True)

        expected_records = [
            {"district_code": district_code, "indicator_id": indicator_id, "raw_value": float(value)}
            for indicator_id, indicator_score in result.indicator_scores.items()
            for district_code, value in indicator_score.raw.items()
            if pd.notna(indicator_score.normalised.get(district_code))
        ]
        expected = pd.DataFrame(expected_records).sort_values(["district_code", "indicator_id"]).reset_index(drop=True)
        pd.testing.assert_frame_equal(stored, expected, check_dtype=False)

    def test_rejects_a_failed_validation(self, pg):
        failed = run_scoring(_raw_values(), INDICATOR_METAS, DISTRICTS + ["UNKNOWN_ONLY_IN_MASTER_LIST"])

        with pytest.raises(ValueError, match="Cannot write a failed scoring run"):
            write_scoring_run(pg, failed, INDICATOR_METAS)

    def test_a_new_run_supersedes_the_previous_one_as_current(self, pg):
        first_run_id = write_scoring_run(pg, _run(), INDICATOR_METAS)
        second_run_id = write_scoring_run(pg, _run(), INDICATOR_METAS)

        with pg.connect() as conn:
            current_ids = conn.execute(
                text("SELECT run_id FROM indices.runs WHERE is_current = true")
            ).scalars().all()

        assert current_ids == [second_run_id]
        assert first_run_id != second_run_id

    def test_missing_indicator_values_are_dropped_not_written(self, pg):
        write_scoring_run(pg, _run(), INDICATOR_METAS)

        with pg.connect() as conn:
            d3_distance_rows = conn.execute(
                text(
                    "SELECT COUNT(*) FROM indicators.indicator_values "
                    "WHERE district_code = 'D3' AND indicator_id = 'health_distance_to_nearest_facility'"
                )
            ).scalar_one()

        assert d3_distance_rows == 0

    def test_the_database_rejects_a_second_row_marked_current(self, pg):
        from sqlalchemy.exc import IntegrityError

        with pg.begin() as conn:
            conn.execute(
                text("INSERT INTO indices.runs (computed_at, is_current) VALUES (now(), true)")
            )

        with pytest.raises(IntegrityError):
            with pg.begin() as conn:
                conn.execute(
                    text("INSERT INTO indices.runs (computed_at, is_current) VALUES (now(), true)")
                )


class TestDistrictMasterList:
    def test_writes_and_reads_back_the_master_list_with_the_urban_flag(self, clean_pg):
        write_district_master_list(clean_pg, DISTRICT_RECORDS, urban_district_names=frozenset({"D3 City"}))

        districts = read_districts(clean_pg).set_index("district_code")

        assert set(districts.index) == {"D1", "D2", "D3"}
        assert districts.loc["D3", "is_urban"]
        assert not districts.loc["D1", "is_urban"]

    def test_a_second_write_upserts_rather_than_duplicates(self, clean_pg):
        write_district_master_list(clean_pg, DISTRICT_RECORDS)
        write_district_master_list(clean_pg, DISTRICT_RECORDS, urban_district_names=frozenset({"D1 Town"}))

        districts = read_districts(clean_pg).set_index("district_code")

        assert len(districts) == len(DISTRICT_RECORDS)
        assert districts.loc["D1", "is_urban"]

    def test_a_score_for_a_district_outside_the_master_list_is_rejected_by_the_database(self, clean_pg):
        from sqlalchemy.exc import IntegrityError

        write_district_master_list(clean_pg, DISTRICT_RECORDS)

        with pytest.raises(IntegrityError):
            with clean_pg.begin() as conn:
                run_id = conn.execute(
                    text("INSERT INTO indices.runs (computed_at, is_current) VALUES (now(), true) RETURNING run_id")
                ).scalar_one()
                conn.execute(
                    text(
                        "INSERT INTO indices.scores "
                        "(run_id, district_code, sector, dimension, score, complete, n_used, n_total) "
                        "VALUES (:run_id, 'NOT_IN_MASTER_LIST', 'Health', NULL, 50.0, true, 1, 1)"
                    ),
                    {"run_id": run_id},
                )


class TestReadFunctions:
    def test_district_decomposition_returns_dimension_and_indicator_rows(self, pg):
        write_scoring_run(pg, _run(), INDICATOR_METAS)

        breakdown = read_district_decomposition(pg, "D1", "Health")

        assert set(breakdown["dimensions"]["dimension"]) == {"Supply", "Access"}
        assert set(breakdown["indicator_values"]["indicator_id"]) == {
            "health_doctor_to_population_ratio",
            "health_distance_to_nearest_facility",
        }

    def test_district_decomposition_indicator_rows_carry_the_raw_value_alongside_the_score(self, pg):
        write_scoring_run(pg, _run(), INDICATOR_METAS)

        indicator_values = read_district_decomposition(pg, "D1", "Health")["indicator_values"].set_index(
            "indicator_id"
        )

        # D1's raw doctor-to-population ratio was submitted as 0.1 (_raw_values above).
        assert indicator_values.loc["health_doctor_to_population_ratio", "raw_value"] == pytest.approx(0.1)

    def test_indicator_cohort_values_returns_every_districts_raw_value_for_one_indicator(self, pg):
        write_scoring_run(pg, _run(), INDICATOR_METAS)

        cohort = read_indicator_cohort_values(pg, "health_doctor_to_population_ratio").set_index("district_code")

        assert cohort.loc["D1", "raw_value"] == pytest.approx(0.1)
        assert cohort.loc["D2", "raw_value"] == pytest.approx(0.3)
        assert cohort.loc["D3", "raw_value"] == pytest.approx(0.5)

    def test_indicator_cohort_values_omits_districts_with_no_value_for_that_indicator(self, pg):
        write_scoring_run(pg, _run(), INDICATOR_METAS)

        # D3's health_distance_to_nearest_facility was deliberately missing in _raw_values.
        cohort = read_indicator_cohort_values(pg, "health_distance_to_nearest_facility")

        assert set(cohort["district_code"]) == {"D1", "D2"}

    def test_sector_cohort_values_returns_every_indicators_raw_values_for_one_sector(self, pg):
        write_scoring_run(pg, _run(), INDICATOR_METAS)

        cohort = read_sector_cohort_values(pg, "Health")

        # Both Health Indicators, keyed so the decomposition can group by Indicator.
        assert set(cohort["indicator_id"]) == {
            "health_doctor_to_population_ratio",
            "health_distance_to_nearest_facility",
        }
        # D1's raw doctor-to-population ratio was submitted as 0.1.
        doctor = cohort[
            (cohort["indicator_id"] == "health_doctor_to_population_ratio")
            & (cohort["district_code"] == "D1")
        ]
        assert doctor["raw_value"].iloc[0] == pytest.approx(0.1)
        # D3's missing Access Indicator is dropped, not imputed — no row.
        assert not (
            (cohort["indicator_id"] == "health_distance_to_nearest_facility")
            & (cohort["district_code"] == "D3")
        ).any()

    def test_national_summary_reflects_the_written_run(self, pg):
        write_scoring_run(pg, _run(), INDICATOR_METAS)

        summary = read_national_summary(pg, "Environment")

        expected_average = _run().sector_scores.query("sector == 'Environment'")["score"].mean()
        assert summary["average"] == pytest.approx(expected_average)
        assert summary["incomplete_count"] == 0


class TestIndicatorMetadata:
    def test_write_indicator_metadata_upserts_reference_years_and_sources(self, clean_pg):
        write_indicator_metadata(
            clean_pg,
            INDICATOR_METAS,
            reference_years={"environment_forest_cover": 2022},
            data_sources={"environment_forest_cover": "Forestry Dept. survey"},
        )

        with clean_pg.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT reference_year, data_source FROM metadata.indicator_definitions "
                    "WHERE indicator_id = 'environment_forest_cover'"
                )
            ).mappings().one()

        assert row["reference_year"] == 2022
        assert row["data_source"] == "Forestry Dept. survey"

    def test_write_indicator_metadata_upserts_a_unit_when_supplied(self, clean_pg):
        write_indicator_metadata(
            clean_pg, INDICATOR_METAS, units={"health_doctor_to_population_ratio": "per 10k"}
        )

        with clean_pg.connect() as conn:
            unit = conn.execute(
                text(
                    "SELECT unit FROM metadata.indicator_definitions "
                    "WHERE indicator_id = 'health_doctor_to_population_ratio'"
                )
            ).scalar_one()

        assert unit == "per 10k"

    def test_write_indicator_metadata_leaves_unit_null_until_supplied(self, clean_pg):
        write_indicator_metadata(clean_pg, INDICATOR_METAS)

        with clean_pg.connect() as conn:
            unit = conn.execute(
                text(
                    "SELECT unit FROM metadata.indicator_definitions "
                    "WHERE indicator_id = 'environment_forest_cover'"
                )
            ).scalar_one()

        assert unit is None

    def test_district_decomposition_indicator_rows_carry_the_unit(self, pg):
        write_indicator_metadata(
            pg, INDICATOR_METAS, units={"health_doctor_to_population_ratio": "per 10k"}
        )
        write_scoring_run(pg, _run(), INDICATOR_METAS)

        indicator_values = read_district_decomposition(pg, "D1", "Health")["indicator_values"].set_index(
            "indicator_id"
        )

        assert indicator_values.loc["health_doctor_to_population_ratio", "unit"] == "per 10k"

    def test_write_indicator_metadata_leaves_objective_null_until_mofnp_supplies_it(self, clean_pg):
        write_indicator_metadata(clean_pg, INDICATOR_METAS)

        with clean_pg.connect() as conn:
            objective = conn.execute(
                text(
                    "SELECT objective FROM metadata.indicator_definitions "
                    "WHERE indicator_id = 'environment_forest_cover'"
                )
            ).scalar_one()

        assert objective is None

    def test_write_indicator_metadata_upserts_an_objective_when_supplied(self, clean_pg):
        write_indicator_metadata(
            clean_pg, INDICATOR_METAS, objectives={"environment_forest_cover": 65.0}
        )

        with clean_pg.connect() as conn:
            objective = conn.execute(
                text(
                    "SELECT objective FROM metadata.indicator_definitions "
                    "WHERE indicator_id = 'environment_forest_cover'"
                )
            ).scalar_one()

        assert objective == pytest.approx(65.0)


class TestSubmissionCatalog:
    def test_write_and_update_a_submission(self, clean_pg):
        submission_id = write_submission(
            clean_pg, file_location="data/raw/health/2026-01-01-mofnp.csv", submitter="mofnp"
        )

        update_submission_status(
            clean_pg,
            submission_id,
            "published",
            validation_report_summary="all checks passed",
            validation_report_path="docs/validation-reports/2026-01-01-health.md",
        )

        with clean_pg.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT status, validation_report_summary, validation_report_path "
                    "FROM catalog.submissions WHERE submission_id = :id"
                ),
                {"id": submission_id},
            ).mappings().one()

        assert row["status"] == "published"
        assert row["validation_report_summary"] == "all checks passed"
        assert row["validation_report_path"] == "docs/validation-reports/2026-01-01-health.md"
