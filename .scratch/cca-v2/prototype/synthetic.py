"""PROTOTYPE — throwaway. In-memory synthetic CCA data for the v2 layout test.

This version mirrors the real scoring engine's shape so the demo behaves
correctly: per indicator it generates a RAW value per district (with a unit),
winsorizes at the 1/99 percentile, then min-max normalises to [0, 100] across
the 116-district cohort (inverting pressure indicators). Sector / Dimension
scores are averages of those normalised indicator scores.

Consequence worth seeing in the demo: the national average of a Sector Index is
NOT 50 — min-max only pins the endpoints, and averaging several 0–100 indicators
pulls the spread toward the middle. That is real behaviour, not a bug.

No Postgres, no scoring engine imported — just plausible numbers. Seeded.
"""

from __future__ import annotations

import json
import os
import warnings

import numpy as np

# A district missing every Indicator in a Dimension yields an all-NaN slice;
# nanmean warns but correctly returns NaN (that district is then excluded).
warnings.filterwarnings("ignore", message="Mean of empty slice", category=RuntimeWarning)

HERE = os.path.dirname(__file__)
SECTORS = ["Health", "Education", "Agriculture", "Infrastructure", "Environment"]

# Per sector: indicators with a Dimension (None for Environment), raw unit,
# a plausible [lo, hi] raw range, orientation, and an optional NDP objective
# (threshold in RAW units) to demonstrate the "objective line" idea.
INDICATORS: dict[str, list[dict]] = {
    "Health": [
        {"key": "hf", "dim": "Supply", "name": "Health facilities per 10k", "unit": "per 10k", "lo": 0.2, "hi": 4.0, "orient": "positive", "threshold": 2.0},
        {"key": "hw", "dim": "Supply", "name": "Skilled health workers per 10k", "unit": "per 10k", "lo": 1, "hi": 25, "orient": "positive", "threshold": 10},
        {"key": "a5", "dim": "Access", "name": "Pop. within 5km of a facility", "unit": "%", "lo": 20, "hi": 99, "orient": "positive", "threshold": 80},
        {"key": "im", "dim": "Access", "name": "Under-5 immunisation coverage", "unit": "%", "lo": 40, "hi": 99, "orient": "positive", "threshold": 90},
    ],
    "Education": [
        {"key": "sc", "dim": "Supply", "name": "Schools per 10k school-age", "unit": "per 10k", "lo": 2, "hi": 20, "orient": "positive", "threshold": None},
        {"key": "tp", "dim": "Supply", "name": "Teachers per 100 pupils", "unit": "per 100", "lo": 1.0, "hi": 6.0, "orient": "positive", "threshold": 3.0},
        {"key": "ne", "dim": "Access", "name": "Net enrolment rate", "unit": "%", "lo": 45, "hi": 99, "orient": "positive", "threshold": 90},
        {"key": "s3", "dim": "Access", "name": "Pop. within 3km of a school", "unit": "%", "lo": 30, "hi": 99, "orient": "positive", "threshold": None},
    ],
    "Agriculture": [
        {"key": "ex", "dim": "Supply", "name": "Extension officers per 10k farmers", "unit": "per 10k", "lo": 0.5, "hi": 12, "orient": "positive", "threshold": None},
        {"key": "ad", "dim": "Supply", "name": "Agro-dealers per district", "unit": "count", "lo": 1, "hi": 40, "orient": "positive", "threshold": None},
        {"key": "fr", "dim": "Access", "name": "Farmers reached by extension", "unit": "%", "lo": 10, "hi": 90, "orient": "positive", "threshold": 60},
        {"key": "su", "dim": "Access", "name": "Input-subsidy coverage", "unit": "%", "lo": 5, "hi": 85, "orient": "positive", "threshold": None},
    ],
    "Infrastructure": [
        {"key": "rd", "dim": "Supply", "name": "Paved-road density", "unit": "km/100km²", "lo": 0.5, "hi": 40, "orient": "positive", "threshold": None},
        {"key": "el", "dim": "Supply", "name": "Grid-electricity coverage", "unit": "%", "lo": 2, "hi": 95, "orient": "positive", "threshold": 50},
        {"key": "wa", "dim": "Access", "name": "Pop. with improved water", "unit": "%", "lo": 25, "hi": 99, "orient": "positive", "threshold": 85},
        {"key": "mo", "dim": "Access", "name": "Mobile-network coverage", "unit": "%", "lo": 40, "hi": 99, "orient": "positive", "threshold": None},
    ],
    "Environment": [
        {"key": "fo", "dim": None, "name": "Forest-cover retention", "unit": "%", "lo": 30, "hi": 99, "orient": "positive", "threshold": None},
        {"key": "ch", "dim": None, "name": "Charcoal-production pressure", "unit": "t/km²", "lo": 0.1, "hi": 12, "orient": "pressure", "threshold": None},
        {"key": "pa", "dim": None, "name": "Protected-area share", "unit": "%", "lo": 0, "hi": 60, "orient": "positive", "threshold": None},
    ],
}

SOURCES = {
    "Health": "Ministry of Health HMIS 2023",
    "Education": "Ministry of Education EMIS 2022",
    "Agriculture": "MoA Crop Forecast Survey 2023",
    "Infrastructure": "RDA / ZESCO returns 2021",
    "Environment": "Forestry Dept / GRID3 2022",
}
REF_YEARS = {"Health": 2023, "Education": 2022, "Agriculture": 2023, "Infrastructure": 2021, "Environment": 2022}
URBAN_NAMES = {"Lusaka", "Ndola", "Kitwe", "Livingstone", "Kabwe", "Chingola"}


def load_districts() -> list[dict]:
    with open(os.path.join(HERE, "districts.json"), encoding="utf-8") as f:
        return json.load(f)


def load_geojson() -> dict:
    with open(os.path.join(HERE, "districts_simplified.geojson"), encoding="utf-8") as f:
        return json.load(f)


def _minmax(raw: np.ndarray, orient: str) -> np.ndarray:
    """Winsorize at 1/99 pct, min-max to [0,100], invert pressure indicators."""
    valid = ~np.isnan(raw)
    out = np.full(raw.shape, np.nan)
    v = raw[valid]
    if v.size == 0:
        return out
    lo, hi = np.nanpercentile(v, 1), np.nanpercentile(v, 99)
    capped = np.clip(raw, lo, hi)
    span = hi - lo
    norm = np.zeros_like(raw) if span == 0 else (capped - lo) / span * 100.0
    if orient == "pressure":
        norm = 100.0 - norm
    out[valid] = norm[valid]
    return out


class Data:
    """Everything the app reads. Arrays are aligned to `codes` order."""

    def __init__(self, districts: list[dict]):
        self.districts = districts
        self.codes = [d["code"] for d in districts]
        self.name_by_code = {d["code"]: d["name"] for d in districts}
        self.prov_by_code = {d["code"]: d["province"] for d in districts}
        self.urban = {d["code"] for d in districts if d["is_urban"]}
        self._build()

    def _build(self) -> None:
        rng = np.random.default_rng(20260902)
        n = len(self.codes)
        dev = rng.normal(0, 1, n)  # per-district development factor, shared across sectors

        # raw[sector][key] and score[sector][key] as arrays aligned to codes
        self.raw: dict[str, dict[str, np.ndarray]] = {}
        self.score: dict[str, dict[str, np.ndarray]] = {}
        self.meta: dict[str, dict[str, dict]] = {}
        for sector in SECTORS:
            self.raw[sector], self.score[sector], self.meta[sector] = {}, {}, {}
            for ind in INDICATORS[sector]:
                lo, hi = ind["lo"], ind["hi"]
                mid = (lo + hi) / 2
                spread = (hi - lo) / 4
                base = mid + dev * spread * 0.7 + rng.normal(0, spread * 0.6, n)
                raw = np.clip(base, lo, hi)
                # ~6% missing per indicator
                missing = rng.random(n) < 0.06
                raw[missing] = np.nan
                self.raw[sector][ind["key"]] = raw
                self.score[sector][ind["key"]] = _minmax(raw, ind["orient"])
                self.meta[sector][ind["key"]] = ind

        # Dimension + Sector Index scores per district (mean of available indicator scores)
        self.overall: dict[str, np.ndarray] = {}
        self.supply: dict[str, np.ndarray] = {}
        self.access: dict[str, np.ndarray] = {}
        self.complete: dict[str, np.ndarray] = {}
        for sector in SECTORS:
            inds = INDICATORS[sector]
            score_stack = np.vstack([self.score[sector][i["key"]] for i in inds])  # (n_ind, n_dist)
            complete = ~np.isnan(score_stack).any(axis=0)
            self.complete[sector] = complete
            if sector == "Environment":
                self.overall[sector] = np.nanmean(score_stack, axis=0)
                self.supply[sector] = np.full(len(self.codes), np.nan)
                self.access[sector] = np.full(len(self.codes), np.nan)
            else:
                sup = np.vstack([self.score[sector][i["key"]] for i in inds if i["dim"] == "Supply"])
                acc = np.vstack([self.score[sector][i["key"]] for i in inds if i["dim"] == "Access"])
                self.supply[sector] = np.nanmean(sup, axis=0)
                self.access[sector] = np.nanmean(acc, axis=0)
                self.overall[sector] = np.nanmean(np.vstack([self.supply[sector], self.access[sector]]), axis=0)

    # ---- lookups the app uses -------------------------------------------
    def measure_array(self, sector: str, measure: str) -> np.ndarray:
        return {"overall": self.overall, "supply": self.supply, "access": self.access}[measure][sector]

    def measure_value(self, sector: str, code: str, measure: str):
        v = self.measure_array(sector, measure)[self.codes.index(code)]
        return None if np.isnan(v) else round(float(v), 1)

    def national_average(self, sector: str, measure: str = "overall") -> float:
        v = self.measure_array(sector, measure)
        return round(float(np.nanmean(v)), 1) if not np.all(np.isnan(v)) else 0.0

    def is_complete(self, sector: str, code: str) -> bool:
        return bool(self.complete[sector][self.codes.index(code)])

    def indicator_rows(self, sector: str, code: str) -> list[dict]:
        i = self.codes.index(code)
        rows = []
        for ind in INDICATORS[sector]:
            raw = self.raw[sector][ind["key"]][i]
            sc = self.score[sector][ind["key"]][i]
            rows.append(
                {
                    "key": ind["key"],
                    "dim": ind["dim"] or "—",
                    "name": ind["name"],
                    "unit": ind["unit"],
                    "raw": None if np.isnan(raw) else float(raw),
                    "score": None if np.isnan(sc) else round(float(sc), 1),
                    "orient": ind["orient"],
                    "threshold": ind["threshold"],
                    "ref_year": REF_YEARS[sector],
                    "source": SOURCES[sector],
                }
            )
        return rows

    def indicator_distribution(self, sector: str, key: str) -> dict:
        """All districts' raw values for one indicator, for the compare-to-others chart."""
        raw = self.raw[sector][key]
        return {"raw": raw, "mean": float(np.nanmean(raw))}
