import numpy as np
import pandas as pd
import pytest

from cca.scoring.engine import (
    IndicatorMeta,
    aggregate,
    decomposition_view,
    normalise,
    orient,
    run_scoring,
    score_indicators,
    validate_full_cohort,
    winsorize,
)

DISTRICTS = [f"D{i:02d}" for i in range(1, 11)]  # small in-memory cohort, not the real 116


def raw(rows):
    return pd.DataFrame(rows, columns=["district_code", "indicator_id", "value"])


class TestFullCohortValidation:
    def test_passes_when_every_master_list_district_is_present(self):
        rows = [(d, "ind_a", 10.0) for d in DISTRICTS]
        result = validate_full_cohort(raw(rows), DISTRICTS)
        assert result.passed
        assert result.reasons == []

    def test_rejects_partial_cohort_without_justification(self):
        rows = [(d, "ind_a", 10.0) for d in DISTRICTS[:5]]
        result = validate_full_cohort(raw(rows), DISTRICTS)
        assert not result.passed
        assert any("Missing districts" in reason for reason in result.reasons)

    def test_allows_partial_cohort_with_explicit_override(self):
        rows = [(d, "ind_a", 10.0) for d in DISTRICTS[:5]]
        result = validate_full_cohort(raw(rows), DISTRICTS, allow_partial=True)
        assert result.passed

    def test_rejects_districts_outside_the_master_list(self):
        rows = [(d, "ind_a", 10.0) for d in DISTRICTS] + [("UNKNOWN", "ind_a", 5.0)]
        result = validate_full_cohort(raw(rows), DISTRICTS)
        assert not result.passed
        assert any("Unknown districts" in reason for reason in result.reasons)

    def test_rejects_duplicate_district_indicator_rows(self):
        rows = [(d, "ind_a", 10.0) for d in DISTRICTS] + [("D01", "ind_a", 20.0)]
        result = validate_full_cohort(raw(rows), DISTRICTS)
        assert not result.passed
        assert any("Duplicate" in reason for reason in result.reasons)


class TestNormalisation:
    def test_min_max_scales_to_0_100(self):
        values = pd.Series([0.0, 5.0, 10.0], index=["a", "b", "c"])
        result = normalise(values)
        assert result["a"] == pytest.approx(0.0)
        assert result["b"] == pytest.approx(50.0)
        assert result["c"] == pytest.approx(100.0)

    def test_recomputed_over_the_full_passed_cohort(self):
        # Same relative value, but the max shifts because the cohort shifts.
        narrow = normalise(pd.Series([0.0, 10.0], index=["a", "b"]))
        wide = normalise(pd.Series([0.0, 10.0, 20.0], index=["a", "b", "c"]))
        assert narrow["b"] == pytest.approx(100.0)
        assert wide["b"] == pytest.approx(50.0)

    def test_constant_indicator_scores_every_present_district_as_100(self):
        values = pd.Series([7.0, 7.0, 7.0], index=["a", "b", "c"])
        result = normalise(values)
        assert (result == 100.0).all()

    def test_missing_values_stay_missing(self):
        values = pd.Series([0.0, np.nan, 10.0], index=["a", "b", "c"])
        result = normalise(values)
        assert pd.isna(result["b"])


class TestOrientation:
    def test_normal_orientation_is_a_no_op(self):
        values = pd.Series([1.0, 2.0], index=["a", "b"])
        assert orient(values, "normal").equals(values)

    def test_invert_flips_the_ranking_before_normalisation(self):
        # A pressure indicator: district "a" has the worst (highest) pressure.
        values = pd.Series([10.0, 5.0, 0.0], index=["a", "b", "c"])
        normalised = normalise(orient(values, "invert"))
        assert normalised["a"] == pytest.approx(0.0)
        assert normalised["c"] == pytest.approx(100.0)


class TestWinsorization:
    def test_extreme_outlier_is_capped_at_the_99th_percentile(self):
        values = pd.Series(
            [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 1000.0],
            index=DISTRICTS,
        )
        capped, report = winsorize("ind_a", values)
        assert capped.max() < 1000.0
        assert capped.max() == pytest.approx(report.upper_bound)
        assert "D10" in report.capped_districts

    def test_distribution_report_captures_pre_and_post_stats(self):
        values = pd.Series(
            [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 1000.0],
            index=DISTRICTS,
        )
        _, report = winsorize("ind_a", values)
        assert report.pre["max"] == pytest.approx(1000.0)
        assert report.post["max"] < report.pre["max"]
        for key in ("min", "max", "mean", "std", "skew"):
            assert key in report.pre
            assert key in report.post

    def test_evenly_spaced_values_are_barely_affected_by_percentile_capping(self):
        values = pd.Series(list(range(10, 20)), index=DISTRICTS, dtype=float)
        capped, report = winsorize("ind_a", values)
        # With no genuine outlier, capping (if any at this small cohort size)
        # barely moves the extremes, unlike the drastic cap for a real outlier.
        assert abs(capped.max() - values.max()) < 1.0
        assert abs(capped.min() - values.min()) < 1.0


class TestAggregation:
    def test_averages_present_indicator_scores_for_a_district(self):
        scores = score_indicators(
            raw(
                [(d, "ind_a", 10.0) for d in DISTRICTS]
                + [(d, "ind_b", 20.0) for d in DISTRICTS]
            ),
            {
                "ind_a": IndicatorMeta("ind_a", "Health", "Supply"),
                "ind_b": IndicatorMeta("ind_b", "Health", "Supply"),
            },
            DISTRICTS,
        )
        result = aggregate(["ind_a", "ind_b"], scores, "D01")
        # Both indicators are constant across the cohort, so both normalise to 100.
        assert result.value == pytest.approx(100.0)
        assert result.complete

    def test_missing_indicator_is_dropped_not_imputed_and_flags_incomplete(self):
        rows = [(d, "ind_a", float(i)) for i, d in enumerate(DISTRICTS)]
        rows += [(d, "ind_b", float(i)) for i, d in enumerate(DISTRICTS) if d != "D01"]
        scores = score_indicators(
            raw(rows),
            {
                "ind_a": IndicatorMeta("ind_a", "Health", "Supply"),
                "ind_b": IndicatorMeta("ind_b", "Health", "Supply"),
            },
            DISTRICTS,
        )
        result = aggregate(["ind_a", "ind_b"], scores, "D01")
        assert not result.complete
        assert result.n_indicators_used == 1
        assert result.n_indicators_total == 2
        # Re-averaged over the remaining indicator only, not imputed as 0/NaN blend.
        assert result.value == pytest.approx(scores["ind_a"].normalised["D01"])


class TestRunScoringSupplyAccessPath:
    def _metas(self):
        return [
            IndicatorMeta("h_supply_1", "Health", "Supply"),
            IndicatorMeta("h_access_1", "Health", "Access"),
        ]

    def _raw(self):
        rows = [(d, "h_supply_1", float(i)) for i, d in enumerate(DISTRICTS)]
        rows += [(d, "h_access_1", float(9 - i)) for i, d in enumerate(DISTRICTS)]
        return raw(rows)

    def test_sector_index_averages_supply_and_access_dimensions(self):
        result = run_scoring(self._raw(), self._metas(), DISTRICTS)
        assert result.validation.passed
        sector_row = result.sector_scores[
            (result.sector_scores.district_code == "D01")
            & (result.sector_scores.sector == "Health")
        ].iloc[0]
        supply = result.dimension_scores[
            (result.dimension_scores.district_code == "D01")
            & (result.dimension_scores.dimension == "Supply")
        ].iloc[0]["score"]
        access = result.dimension_scores[
            (result.dimension_scores.district_code == "D01")
            & (result.dimension_scores.dimension == "Access")
        ].iloc[0]["score"]
        assert sector_row["score"] == pytest.approx((supply + access) / 2)

    def test_invalid_cohort_short_circuits_with_no_scores(self):
        partial = self._raw()
        partial = partial[partial.district_code != "D01"]
        result = run_scoring(partial, self._metas(), DISTRICTS)
        assert not result.validation.passed
        assert result.sector_scores.empty


class TestEnvironmentDimensionlessPath:
    def _metas(self):
        return [
            IndicatorMeta("env_condition", "Environment", None, orientation="normal"),
            IndicatorMeta("env_pressure", "Environment", None, orientation="invert"),
        ]

    def _raw(self):
        # D01 has the best condition and the lowest pressure; D10 the worst of each.
        rows = [(d, "env_condition", float(9 - i)) for i, d in enumerate(DISTRICTS)]
        rows += [(d, "env_pressure", float(i)) for i, d in enumerate(DISTRICTS)]
        return raw(rows)

    def test_indicators_average_directly_into_the_sector_index_with_no_dimension_rows(self):
        result = run_scoring(self._raw(), self._metas(), DISTRICTS)
        assert result.dimension_scores.empty
        row = result.sector_scores[
            (result.sector_scores.district_code == "D01")
            & (result.sector_scores.sector == "Environment")
        ].iloc[0]
        # condition is highest for D01 -> 100; pressure is lowest for D01, and
        # inversion turns "lowest raw pressure" into the highest score -> 100.
        assert row["score"] == pytest.approx((100.0 + 100.0) / 2)

    def test_pressure_indicator_inversion_pulls_high_pressure_districts_down(self):
        result = run_scoring(self._raw(), self._metas(), DISTRICTS)
        best = result.sector_scores[
            (result.sector_scores.district_code == "D01")
            & (result.sector_scores.sector == "Environment")
        ].iloc[0]["score"]
        worst = result.sector_scores[
            (result.sector_scores.district_code == "D10")
            & (result.sector_scores.sector == "Environment")
        ].iloc[0]["score"]
        assert best > worst


class TestDecompositionView:
    def test_traces_a_sector_index_down_to_dimension_and_indicator_scores(self):
        metas = [
            IndicatorMeta("h_supply_1", "Health", "Supply"),
            IndicatorMeta("h_access_1", "Health", "Access"),
        ]
        rows = [(d, "h_supply_1", float(i)) for i, d in enumerate(DISTRICTS)]
        rows += [(d, "h_access_1", float(9 - i)) for i, d in enumerate(DISTRICTS)]
        scores = score_indicators(
            raw(rows), {m.indicator_id: m for m in metas}, DISTRICTS
        )
        breakdown = decomposition_view("Health", "D01", metas, scores)
        assert set(breakdown.keys()) == {"Supply", "Access"}
        assert breakdown["Supply"]["indicators"][0]["indicator_id"] == "h_supply_1"
        assert breakdown["Supply"]["complete"]
