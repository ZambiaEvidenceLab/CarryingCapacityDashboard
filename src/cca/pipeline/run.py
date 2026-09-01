"""End-to-end validation and publish pipeline (spec: "Validation and publish pipeline", ADR-0012).

Orchestrates the adapters built by earlier tickets — GRID3 (03), Postgres
I/O (05) — plus this ticket's own validation steps (district-name matching,
range/type constraints, the ADR-0015 report) around the pure scoring engine.
For v1 this is invoked manually, e.g. from a GitHub Actions
`workflow_dispatch` job (see `scripts/run_pipeline.py`).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine

from cca.grid3.client import District
from cca.pipeline._paths import next_available_path
from cca.pipeline.constraints import check_constraints
from cca.pipeline.district_matching import match_district_names
from cca.pipeline.report import build_report, write_report
from cca.scoring.engine import (
    IndicatorMeta,
    ValidationResult,
    run_scoring,
    score_indicators,
    validate_full_cohort,
)
from cca.scoring.indicators import CCA_INDICATORS
from cca.storage.io import update_submission_status, write_scoring_run, write_submission

_EXCEL_SUFFIXES = {".xlsx", ".xls"}


@dataclass
class PipelineResult:
    submission_id: int
    status: str  # "published" or "rejected"
    validation: ValidationResult
    report_path: str
    run_id: int | None = None


def _read_raw_file(path: Path) -> pd.DataFrame:
    """Load a submitted district-name-keyed raw file (columns: district_name, indicator_id, value)."""
    if path.suffix.lower() in _EXCEL_SUFFIXES:
        return pd.read_excel(path)
    return pd.read_csv(path)


def _store_in_data_lake(
    source_file: Path, *, data_lake_root: Path, sector: str, submitted_at: datetime, submitter: str
) -> Path:
    """Copy `source_file` into `data/raw/<sector>/<date>-<submitter><ext>` (ADR-0016), never overwriting."""
    sector_dir = data_lake_root / sector.lower()
    sector_dir.mkdir(parents=True, exist_ok=True)

    stem = f"{submitted_at:%Y-%m-%d}-{submitter}"
    dest = next_available_path(sector_dir, stem, source_file.suffix)
    shutil.copyfile(source_file, dest)
    return dest


def run_validation_and_publish(
    engine: Engine,
    source_file: str | Path,
    *,
    sector: str,
    submitter: str,
    districts: list[District],
    indicator_metas: list[IndicatorMeta] | None = None,
    data_lake_root: str | Path = "data/raw",
    reports_root: str | Path = "docs/validation-reports",
    submitted_at: datetime | None = None,
) -> PipelineResult:
    """Validate one raw submission and, if it fully passes, publish it (ADR-0012).

    Stores the raw file and creates a `pending` catalog entry unconditionally
    (a submission is tracked even if it goes on to fail, and the raw file is
    never deleted). Validation runs district-name matching against the GRID3
    master list, the 116-district full-cohort check, and per-indicator
    range/type constraints; a fully passing run also runs the scoring engine
    and writes a new current run to the processed layer. Either way, the
    validation/winsorization report is written to the repo and referenced
    from the catalog entry (ADR-0015).
    """
    source_file = Path(source_file)
    submitted_at = submitted_at or datetime.now(timezone.utc)
    district_codes = [d.code for d in districts]

    stored_path = _store_in_data_lake(
        source_file, data_lake_root=Path(data_lake_root), sector=sector, submitted_at=submitted_at, submitter=submitter
    )
    submission_id = write_submission(
        engine, file_location=str(stored_path), submitter=submitter, submitted_at=submitted_at, status="pending"
    )

    raw_values = _read_raw_file(stored_path)

    if indicator_metas is None:
        # Score only the indicators this submission actually contains. Every
        # pipeline run recomputes and overwrites *all* sectors' current
        # scores (schema.py: one global `is_current` run, not one per
        # sector) — scoring against the full CCA_INDICATORS catalog here
        # would silently blank out every other sector's still-valid
        # published scores whenever a submission covers only one sector.
        submitted_ids = set(raw_values["indicator_id"])
        indicator_metas = [m for m in CCA_INDICATORS if m.indicator_id in submitted_ids]

    mapped, name_validation = match_district_names(raw_values, districts)
    cohort_validation = validate_full_cohort(mapped, district_codes)
    # Constraint checking runs on every submitted row, labelled by the
    # original district_name -- rows that failed name-matching still get a
    # meaningful reason string, and mapped's district_code is unavailable
    # for them.
    constraint_validation = check_constraints(
        raw_values, [m.indicator_id for m in indicator_metas], id_column="district_name"
    )

    reasons = name_validation.reasons + cohort_validation.reasons + constraint_validation.reasons
    passed = not reasons
    validation = ValidationResult(passed=passed, reasons=reasons)

    winsorization_reports = {}
    if not mapped.empty:
        meta_by_id = {m.indicator_id: m for m in indicator_metas if m.indicator_id in set(mapped["indicator_id"])}
        if meta_by_id:
            scored = score_indicators(mapped, meta_by_id, district_codes)
            winsorization_reports = {iid: s.winsorization for iid, s in scored.items()}

    report_markdown = build_report(
        sector=sector,
        submitter=submitter,
        submitted_at=submitted_at,
        validation=validation,
        winsorization_reports=winsorization_reports,
    )
    report_relative_path = write_report(
        report_markdown, reports_root=reports_root, sector=sector, submitted_at=submitted_at, submitter=submitter
    )
    report_path = str(Path(reports_root) / report_relative_path)
    summary = "; ".join(reasons) if reasons else "All checks passed"

    run_id = None
    if passed:
        scoring_result = run_scoring(mapped, indicator_metas, district_codes)
        run_id = write_scoring_run(engine, scoring_result, indicator_metas, computed_at=submitted_at)
        status = "published"
    else:
        status = "rejected"

    update_submission_status(
        engine, submission_id, status, validation_report_summary=summary, validation_report_path=report_path
    )

    return PipelineResult(
        submission_id=submission_id,
        status=status,
        validation=validation,
        report_path=report_path,
        run_id=run_id,
    )
