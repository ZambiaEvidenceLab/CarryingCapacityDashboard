import pandas as pd
import pytest

from cca.pipeline.constraints import check_constraints


def _row(indicator_id, value, district_code="D001"):
    return {"district_code": district_code, "indicator_id": indicator_id, "value": value}


class TestCheckConstraints:
    def test_passes_values_within_the_known_plausible_range(self):
        raw = pd.DataFrame([_row("health_skilled_birth_attendance_rate", 55.0)])

        result = check_constraints(raw, ["health_skilled_birth_attendance_rate"])

        assert result.passed

    def test_rejects_a_value_outside_the_plausible_range(self):
        raw = pd.DataFrame([_row("health_skilled_birth_attendance_rate", 250.0)])

        result = check_constraints(raw, ["health_skilled_birth_attendance_rate"])

        assert not result.passed
        assert any("health_skilled_birth_attendance_rate" in reason for reason in result.reasons)

    def test_rejects_a_non_numeric_value(self):
        raw = pd.DataFrame([_row("health_skilled_birth_attendance_rate", "not-a-number")])

        result = check_constraints(raw, ["health_skilled_birth_attendance_rate"])

        assert not result.passed
        assert any("D001" in reason for reason in result.reasons)

    def test_rejects_an_indicator_id_outside_the_catalog(self):
        raw = pd.DataFrame([_row("not_a_real_indicator", 1.0)])

        result = check_constraints(raw, ["health_skilled_birth_attendance_rate"])

        assert not result.passed
        assert any("not_a_real_indicator" in reason for reason in result.reasons)

    def test_a_missing_value_is_not_flagged_here_completeness_is_handled_by_the_scoring_engine(self):
        raw = pd.DataFrame([_row("health_skilled_birth_attendance_rate", float("nan"))])

        result = check_constraints(raw, ["health_skilled_birth_attendance_rate"])

        assert result.passed
