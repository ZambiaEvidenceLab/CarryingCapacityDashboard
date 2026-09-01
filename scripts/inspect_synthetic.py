"""Ad-hoc inspection of the synthetic data generator's output.

Not part of the CCA package — a developer tool for eyeballing what
`cca.synthetic.generator` produces (coverage, missing values, winsorization
capping, resulting Sector Index scores) before wiring it into the pipeline
or dashboard. Run with the project venv:

    .venv/Scripts/python.exe scripts/inspect_synthetic.py
"""

from pathlib import Path

import pandas as pd

from cca.grid3.client import fetch_district_master_list
from cca.scoring.engine import run_scoring
from cca.scoring.indicators import CCA_INDICATORS
from cca.synthetic.generator import generate_synthetic_dataset

GRID3_CACHE_PATH = Path(__file__).parent / ".grid3_districts_cache.json"

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)
pd.set_option("display.max_rows", 40)

districts = fetch_district_master_list(GRID3_CACHE_PATH)
district_codes = [d.code for d in districts]
print(f"Fetched {len(districts)} districts from GRID3 (cached at {GRID3_CACHE_PATH})")

raw = generate_synthetic_dataset(districts, seed=7)

print("\n=== Raw synthetic data ===")
print(f"Rows: {len(raw)} (out of a full grid of {len(districts) * len(CCA_INDICATORS)} district x indicator cells)")
print(raw.head(10).to_string(index=False))

print("\n=== Missing values per indicator (out of 116 districts) ===")
present_counts = raw.groupby("indicator_id")["district_code"].nunique()
missing_counts = (len(districts) - present_counts).sort_values(ascending=False)
print(missing_counts.to_string())

print("\n=== Value distribution per indicator ===")
print(raw.groupby("indicator_id")["value"].describe()[["min", "mean", "max", "std"]].to_string())

result = run_scoring(raw, CCA_INDICATORS, district_codes)

print("\n=== Validation ===")
print(f"Passed: {result.validation.passed}")
if result.validation.reasons:
    print(result.validation.reasons)

print("\n=== Winsorization capping (indicators with at least one capped district) ===")
for indicator_id, report in result.winsorization_reports.items():
    if report.capped_districts:
        print(f"{indicator_id}: capped {len(report.capped_districts)} districts "
              f"(bounds [{report.lower_bound:.2f}, {report.upper_bound:.2f}])")

print("\n=== Sector scores (head) ===")
print(result.sector_scores.head(10).to_string(index=False))

print("\n=== Data completeness (True/False count per sector) ===")
print(result.sector_scores.groupby("sector")["complete"].value_counts().to_string())
