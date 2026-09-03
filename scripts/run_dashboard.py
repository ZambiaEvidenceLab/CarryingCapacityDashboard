"""CLI entrypoint for the Dash dashboard (ADR-0005).

    .venv/Scripts/python.exe scripts/run_dashboard.py

Reads the database connection string from `CCA_DATABASE_URL`, the GRID3
cache path from `CCA_GRID3_CACHE_PATH` (defaults to
`scripts/.grid3_districts_cache.json`, matching `run_pipeline.py`), and the
simplified-boundary cache path from `CCA_GRID3_SIMPLIFIED_CACHE_PATH`
(defaults to `scripts/.grid3_districts_simplified_cache.json`). The app
itself performs no calculation (ADR-0010) and never simplifies at page load
(ADR-0017) — it only reads the processed Postgres layer and the cached
GRID3 boundaries this reuses without a network call or a shapely pass.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

from cca.dashboard.app import build_app
from cca.grid3.client import fetch_district_master_list
from cca.grid3.simplify import ensure_simplified_boundary_cache

load_dotenv()

DEFAULT_GRID3_CACHE_PATH = Path(__file__).parent / ".grid3_districts_cache.json"
DEFAULT_GRID3_SIMPLIFIED_CACHE_PATH = Path(__file__).parent / ".grid3_districts_simplified_cache.json"


def main() -> None:
    database_url = os.environ["CCA_DATABASE_URL"]
    grid3_cache_path = Path(os.environ.get("CCA_GRID3_CACHE_PATH", DEFAULT_GRID3_CACHE_PATH))
    grid3_simplified_cache_path = Path(
        os.environ.get("CCA_GRID3_SIMPLIFIED_CACHE_PATH", DEFAULT_GRID3_SIMPLIFIED_CACHE_PATH)
    )

    engine = create_engine(database_url)
    districts = fetch_district_master_list(grid3_cache_path)
    simplified_districts = ensure_simplified_boundary_cache(districts, grid3_simplified_cache_path)

    app = build_app(engine, simplified_districts)
    app.run(debug=os.environ.get("CCA_DASHBOARD_DEBUG", "false").lower() == "true")


if __name__ == "__main__":
    main()
