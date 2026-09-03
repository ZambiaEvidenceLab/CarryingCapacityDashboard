"""Seed a database with synthetic data end-to-end, for local dashboard demos.

Populates the district master list, the indicator catalog, and a full
scoring run from `cca.synthetic.generator` -- everything the dashboard
(`scripts/run_dashboard.py`) needs to render without touching real MoFNP
data. Intended for a scratch/dev database, not `cca_test` (the automated
test suite truncates that one before every test).

    .venv/Scripts/python.exe scripts/seed_synthetic_data.py

Reads the database connection string from `CCA_DATABASE_URL` (defaults to
the local `cca_dev` database) and the GRID3 cache path from
`CCA_GRID3_CACHE_PATH` (defaults to `scripts/.grid3_districts_cache.json`,
matching `run_pipeline.py`/`run_dashboard.py`). Pass `--seed` to vary the
synthetic values, `--urban-district` (repeatable) to flag which districts
get the Urban annotation.
"""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from cca.grid3.client import fetch_district_master_list
from cca.scoring.engine import run_scoring
from cca.scoring.indicators import CCA_INDICATORS
from cca.storage.io import write_district_master_list, write_indicator_metadata, write_scoring_run
from cca.storage.schema import create_all
from cca.synthetic.generator import generate_synthetic_dataset

load_dotenv()

# Plausible raw-unit labels for the demo, so the decomposition's raw values and
# compare-to-others charts (ticket 07) read with a unit rather than a bare
# number. Demo-only — the real catalog will carry MoFNP-supplied units.
SYNTHETIC_UNITS: dict[str, str] = {
    "health_doctor_to_population_ratio": "per 1k",
    "health_nurse_to_population_ratio": "per 1k",
    "health_facilities_with_functional_emonc": "facilities",
    "health_skilled_birth_attendance_rate": "%",
    "health_distance_to_nearest_facility": "km",
    "health_pct_population_registered_nhima": "%",
    "education_pupil_teacher_ratio_primary": "pupils/teacher",
    "education_pupil_teacher_ratio_secondary": "pupils/teacher",
    "education_electrification_of_schools": "%",
    "education_schools_with_internet": "%",
    "education_distance_to_nearest_school": "km",
    "education_mean_years_of_schooling": "years",
    "agriculture_extension_worker_to_farmer_ratio": "farmers/worker",
    "agriculture_maize_production_per_capita": "MT/person",
    "agriculture_fra_storage_tonnes_per_capita": "tonnes/person",
    "agriculture_pct_population_receiving_fisp": "%",
    "agriculture_pct_farmers_reached_by_extension": "%",
    "infrastructure_water_point_density": "per 1k",
    "infrastructure_grid_connection_capacity": "kVA/1k",
    "infrastructure_network_tower_coverage": "%",
    "infrastructure_pct_households_safe_water": "%",
    "infrastructure_distance_to_nearest_water_point": "km",
    "infrastructure_pct_households_electrified": "%",
    "environment_forest_cover": "%",
    "environment_ecological_diversity": "index",
    "environment_population_growth_rate": "%/yr",
    "environment_cattlehead_per_capita": "head/person",
    "environment_charcoal_consumption_domestic": "kg/hh",
}

DEFAULT_DATABASE_URL = "postgresql+psycopg://cca_dev:cca_dev_local_only@localhost:5432/cca_dev"
DEFAULT_GRID3_CACHE_PATH = Path(__file__).parent / ".grid3_districts_cache.json"
DEFAULT_URBAN_DISTRICTS = frozenset({"Lusaka", "Ndola", "Kitwe", "Livingstone"})

TABLES_TO_TRUNCATE = (
    "catalog.submissions",
    "indicators.indicator_values",
    "indices.scores",
    "indices.runs",
    "metadata.indicator_definitions",
    "metadata.districts",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7, help="Synthetic data RNG seed (default: 7)")
    parser.add_argument(
        "--urban-district",
        dest="urban_districts",
        action="append",
        help="District name to flag as mostly-urban (repeatable). Defaults to Lusaka/Ndola/Kitwe/Livingstone.",
    )
    args = parser.parse_args(argv)
    urban_districts = frozenset(args.urban_districts) if args.urban_districts else DEFAULT_URBAN_DISTRICTS

    database_url = os.environ.get("CCA_DATABASE_URL", DEFAULT_DATABASE_URL)
    grid3_cache_path = Path(os.environ.get("CCA_GRID3_CACHE_PATH", DEFAULT_GRID3_CACHE_PATH))

    engine = create_engine(database_url)
    create_all(engine)

    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(TABLES_TO_TRUNCATE)} RESTART IDENTITY CASCADE"))

    districts = fetch_district_master_list(grid3_cache_path)
    write_district_master_list(engine, districts, urban_district_names=urban_districts)
    write_indicator_metadata(
        engine,
        CCA_INDICATORS,
        reference_years={meta.indicator_id: 2023 for meta in CCA_INDICATORS},
        data_sources={meta.indicator_id: "Synthetic demo data" for meta in CCA_INDICATORS},
        units=SYNTHETIC_UNITS,
    )

    raw = generate_synthetic_dataset(districts, seed=args.seed)
    result = run_scoring(raw, CCA_INDICATORS, [d.code for d in districts])
    if not result.validation.passed:
        print("Synthetic data failed validation:")
        for reason in result.validation.reasons:
            print(f"  - {reason}")
        return 1

    run_id = write_scoring_run(engine, result, CCA_INDICATORS)
    print(f"Seeded {len(districts)} districts and run {run_id} into {database_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
