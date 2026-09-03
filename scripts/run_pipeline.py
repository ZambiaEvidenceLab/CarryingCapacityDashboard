"""CLI entrypoint for the validation and publish pipeline (ADR-0012).

Invoked manually for v1 — a developer/data steward's own machine, or a
GitHub Actions `workflow_dispatch` job (see
`.github/workflows/publish-data.yml`) — never automatically on a schedule or
webhook.

    .venv/Scripts/python.exe scripts/run_pipeline.py \\
        --file path/to/submission.csv --sector Health --submitter mofnp

Reads the database connection string from `CCA_DATABASE_URL`, the GRID3
cache path from `CCA_GRID3_CACHE_PATH` (defaults to
`scripts/.grid3_districts_cache.json`, matching `inspect_synthetic.py`), and
the simplified-boundary cache path from `CCA_GRID3_SIMPLIFIED_CACHE_PATH`
(defaults to `scripts/.grid3_districts_simplified_cache.json`, matching
`run_dashboard.py`). Boundary simplification (ADR-0017) runs here, at the
data-refresh cycle, so the dashboard never has to.
"""

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine

from cca.grid3.client import fetch_district_master_list
from cca.grid3.simplify import ensure_simplified_boundary_cache
from cca.pipeline.run import run_validation_and_publish
from cca.storage.io import write_district_master_list
from cca.storage.schema import create_all

DEFAULT_GRID3_CACHE_PATH = Path(__file__).parent / ".grid3_districts_cache.json"
DEFAULT_GRID3_SIMPLIFIED_CACHE_PATH = Path(__file__).parent / ".grid3_districts_simplified_cache.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, type=Path, help="Path to the raw Excel/CSV submission")
    parser.add_argument("--sector", required=True, help="Sector this submission belongs to (e.g. Health)")
    parser.add_argument("--submitter", required=True, help="Who submitted this file (used in the audit trail)")
    args = parser.parse_args(argv)

    database_url = os.environ["CCA_DATABASE_URL"]
    grid3_cache_path = Path(os.environ.get("CCA_GRID3_CACHE_PATH", DEFAULT_GRID3_CACHE_PATH))
    grid3_simplified_cache_path = Path(
        os.environ.get("CCA_GRID3_SIMPLIFIED_CACHE_PATH", DEFAULT_GRID3_SIMPLIFIED_CACHE_PATH)
    )

    engine = create_engine(database_url)
    create_all(engine)
    districts = fetch_district_master_list(grid3_cache_path)
    # Every score/indicator-value row is foreign-keyed to metadata.districts
    # (schema.py) -- keep it in sync with the GRID3 master list on every run.
    write_district_master_list(engine, districts)
    ensure_simplified_boundary_cache(districts, grid3_simplified_cache_path)

    result = run_validation_and_publish(
        engine, args.file, sector=args.sector, submitter=args.submitter, districts=districts
    )

    print(f"Submission {result.submission_id}: {result.status}")
    print(f"Validation report: {result.report_path}")
    if not result.validation.passed:
        print("Rejection reasons:")
        for reason in result.validation.reasons:
            print(f"  - {reason}")
        return 1

    print(f"Published as run {result.run_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
