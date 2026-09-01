"""CLI entrypoint for the Dash dashboard (ADR-0005).

    .venv/Scripts/python.exe scripts/run_dashboard.py

Reads the database connection string from `CCA_DATABASE_URL` and the GRID3
cache path from `CCA_GRID3_CACHE_PATH` (defaults to
`scripts/.grid3_districts_cache.json`, matching `run_pipeline.py`). The app
itself performs no calculation (ADR-0010) — it only reads the processed
Postgres layer and the cached GRID3 boundaries this reuses without a network
call.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine

from cca.dashboard.app import build_app
from cca.grid3.client import fetch_district_master_list

DEFAULT_GRID3_CACHE_PATH = Path(__file__).parent / ".grid3_districts_cache.json"


def main() -> None:
    database_url = os.environ["CCA_DATABASE_URL"]
    grid3_cache_path = Path(os.environ.get("CCA_GRID3_CACHE_PATH", DEFAULT_GRID3_CACHE_PATH))

    engine = create_engine(database_url)
    districts = fetch_district_master_list(grid3_cache_path)

    app = build_app(engine, districts)
    app.run(debug=os.environ.get("CCA_DASHBOARD_DEBUG", "false").lower() == "true")


if __name__ == "__main__":
    main()
