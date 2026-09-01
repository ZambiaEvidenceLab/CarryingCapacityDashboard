"""Validation report generation for the publish pipeline (ADR-0015).

`build_report` is a pure function (markdown in, no I/O) so its content is
unit-testable without touching the filesystem; `write_report` is the thin
adapter that commits it to the repo at a stable, collision-free path.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from cca.pipeline._paths import next_available_path
from cca.scoring.engine import ValidationResult, WinsorizationReport


def build_report(
    *,
    sector: str,
    submitter: str,
    submitted_at: datetime,
    validation: ValidationResult,
    winsorization_reports: dict[str, WinsorizationReport],
) -> str:
    """Render the pass/fail outcome, rejection reasons, and winsorization/distribution report as Markdown."""
    outcome = "PASSED" if validation.passed else "REJECTED"
    lines = [
        f"# Validation report: {sector} submission from {submitter}",
        "",
        f"- Submitted at: {submitted_at.isoformat()}",
        f"- Sector: {sector}",
        f"- Submitter: {submitter}",
        f"- Outcome: **{outcome}**",
        "",
    ]

    if validation.reasons:
        lines.append("## Reasons")
        lines.extend(f"- {reason}" for reason in validation.reasons)
        lines.append("")

    if winsorization_reports:
        lines.append("## Winsorization / distribution report")
        lines.append("")
        lines.append("| Indicator | Lower bound | Upper bound | Capped districts | Pre mean | Post mean | Pre std | Post std |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for indicator_id, report in sorted(winsorization_reports.items()):
            lines.append(
                f"| {indicator_id} | {report.lower_bound:.4g} | {report.upper_bound:.4g} | "
                f"{', '.join(report.capped_districts) or '-'} | {report.pre['mean']:.4g} | "
                f"{report.post['mean']:.4g} | {report.pre['std']:.4g} | {report.post['std']:.4g} |"
            )
        lines.append("")

    return "\n".join(lines)


def write_report(
    markdown: str,
    *,
    reports_root: str | Path,
    sector: str,
    submitted_at: datetime,
    submitter: str,
) -> Path:
    """Write the report under `reports_root`, returning its path relative to `reports_root`.

    Filenames are date + sector + submitter, with a numeric suffix appended
    on collision (e.g. two submissions from the same submitter/sector on the
    same day) so an existing report is never overwritten.
    """
    reports_root = Path(reports_root)
    reports_root.mkdir(parents=True, exist_ok=True)

    stem = f"{submitted_at:%Y-%m-%d}-{sector.lower()}-{submitter}"
    path = next_available_path(reports_root, stem, ".md")

    path.write_text(markdown)
    return path.relative_to(reports_root)
