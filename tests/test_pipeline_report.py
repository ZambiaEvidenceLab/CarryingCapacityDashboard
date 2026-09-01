from datetime import datetime, timezone

from cca.scoring.engine import ValidationResult, WinsorizationReport
from cca.pipeline.report import build_report, write_report

SUBMITTED_AT = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)


class TestBuildReport:
    def test_a_passing_report_states_the_outcome_and_submission_metadata(self):
        markdown = build_report(
            sector="Health",
            submitter="mofnp",
            submitted_at=SUBMITTED_AT,
            validation=ValidationResult(passed=True, reasons=[]),
            winsorization_reports={},
        )

        assert "PASSED" in markdown
        assert "Health" in markdown
        assert "mofnp" in markdown
        assert "2026-01-15" in markdown

    def test_a_failing_report_lists_every_rejection_reason(self):
        markdown = build_report(
            sector="Health",
            submitter="mofnp",
            submitted_at=SUBMITTED_AT,
            validation=ValidationResult(passed=False, reasons=["Unknown districts: ['X']", "Bad value at D1"]),
            winsorization_reports={},
        )

        assert "REJECTED" in markdown
        assert "Unknown districts: ['X']" in markdown
        assert "Bad value at D1" in markdown

    def test_includes_the_winsorization_distribution_report_per_indicator(self):
        report = WinsorizationReport(
            indicator_id="health_doctor_to_population_ratio",
            lower_bound=0.05,
            upper_bound=0.45,
            capped_districts=["D001"],
            pre={"min": 0.01, "max": 0.9, "mean": 0.2, "std": 0.1, "skew": 0.5},
            post={"min": 0.05, "max": 0.45, "mean": 0.2, "std": 0.09, "skew": 0.3},
        )
        markdown = build_report(
            sector="Health",
            submitter="mofnp",
            submitted_at=SUBMITTED_AT,
            validation=ValidationResult(passed=True, reasons=[]),
            winsorization_reports={"health_doctor_to_population_ratio": report},
        )

        assert "health_doctor_to_population_ratio" in markdown
        assert "D001" in markdown
        assert "0.05" in markdown


class TestWriteReport:
    def test_writes_the_report_under_the_sector_and_date_and_returns_a_relative_path(self, tmp_path):
        reports_root = tmp_path / "docs" / "validation-reports"

        relative_path = write_report(
            "# report body",
            reports_root=reports_root,
            sector="Health",
            submitted_at=SUBMITTED_AT,
            submitter="mofnp",
        )

        written = reports_root / relative_path.name
        assert written.exists()
        assert written.read_text() == "# report body"
        assert "2026-01-15" in relative_path.name
        assert "health" in relative_path.name.lower()

    def test_a_second_report_the_same_day_does_not_clobber_the_first(self, tmp_path):
        reports_root = tmp_path / "docs" / "validation-reports"

        first = write_report("first", reports_root=reports_root, sector="Health",
                              submitted_at=SUBMITTED_AT, submitter="mofnp")
        second = write_report("second", reports_root=reports_root, sector="Health",
                               submitted_at=SUBMITTED_AT, submitter="mofnp")

        assert first != second
        assert (reports_root / first.name).read_text() == "first"
        assert (reports_root / second.name).read_text() == "second"
