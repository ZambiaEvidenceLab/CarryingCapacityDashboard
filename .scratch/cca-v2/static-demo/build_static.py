"""PROTOTYPE — throwaway. Builds a self-contained static index.html for GitHub
Pages from the prototype's synthetic data.

The static page is a client-side reimplementation of the map-hero flow: it does
no calculation (mirrors ADR-0010), it only reads precomputed synthetic scores
baked into the page as JSON and draws them with Plotly.js (from CDN) + vanilla
JS. No server, no database — publishable as a plain static file.

Run:  ../../../.venv/Scripts/python.exe build_static.py
Output: index.html (self-contained apart from the Plotly CDN script).
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "prototype"))

from synthetic import INDICATORS, SECTORS, Data, load_districts, load_geojson  # noqa: E402

# Per-sector single-hue ramps, light (low capacity) -> dark (high). Mirrors the
# Dash prototype's SECTOR_RAMPS.
SECTOR_RAMPS = {
    "Health": [[0.0, "#FCE9E6"], [0.5, "#E0806A"], [1.0, "#8C2D24"]],
    "Education": [[0.0, "#E7F0F8"], [0.5, "#6FA3D2"], [1.0, "#173F66"]],
    "Agriculture": [[0.0, "#E4F2EA"], [0.5, "#6FB894"], [1.0, "#1C5E41"]],
    "Infrastructure": [[0.0, "#EFEAF6"], [0.5, "#9E86C6"], [1.0, "#432C74"]],
    "Environment": [[0.0, "#FBF1DD"], [0.5, "#DBAA5A"], [1.0, "#7A5314"]],
}
MEASURES = {s: (["overall"] if s == "Environment" else ["overall", "supply", "access"]) for s in SECTORS}


def _round(x, n=1):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


def build_payload() -> dict:
    D = Data(load_districts())
    codes = D.codes
    districts = [
        {"code": c, "name": D.name_by_code[c], "province": D.prov_by_code[c], "urban": c in D.urban}
        for c in codes
    ]

    scores, complete, nat_avg = {}, {}, {}
    for s in SECTORS:
        scores[s] = {}
        for m in ("overall", "supply", "access"):
            arr = D.measure_array(s, m)
            scores[s][m] = [_round(v) for v in arr]
        complete[s] = [bool(x) for x in D.complete[s]]
        nat_avg[s] = {m: D.national_average(s, m) for m in MEASURES[s]}

    ind_meta, ind_raw, ind_score = {}, {}, {}
    for s in SECTORS:
        ind_meta[s] = [
            {
                "key": i["key"],
                "dim": i["dim"] or "—",
                "name": i["name"],
                "unit": i["unit"],
                "threshold": i["threshold"],
                "ref_year": D.meta[s][i["key"]]["ref_year"] if "ref_year" in D.meta[s][i["key"]] else None,
            }
            for i in INDICATORS[s]
        ]
        ind_raw[s] = {i["key"]: [_round(v, 2) for v in D.raw[s][i["key"]]] for i in INDICATORS[s]}
        ind_score[s] = {i["key"]: [_round(v) for v in D.score[s][i["key"]]] for i in INDICATORS[s]}

    # ref_year / source live in synthetic.REF_YEARS / SOURCES
    from synthetic import REF_YEARS, SOURCES

    for s in SECTORS:
        for row in ind_meta[s]:
            row["ref_year"] = REF_YEARS[s]
            row["source"] = SOURCES[s]

    return {
        "sectors": SECTORS,
        "measures": MEASURES,
        "ramps": SECTOR_RAMPS,
        "rampDark": {s: SECTOR_RAMPS[s][-1][1] for s in SECTORS},
        "districts": districts,
        "geojson": load_geojson(),
        "scores": scores,
        "complete": complete,
        "natAvg": nat_avg,
        "indMeta": ind_meta,
        "indRaw": ind_raw,
        "indScore": ind_score,
    }


def main() -> None:
    payload = build_payload()
    template_path = os.path.join(HERE, "template.html")
    with open(template_path, encoding="utf-8") as f:
        template = f.read()
    html = template.replace("/*__PAYLOAD__*/null", json.dumps(payload, separators=(",", ":")))
    out = os.path.join(HERE, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {out}  ({os.path.getsize(out) / 1024:,.0f} KB)")


if __name__ == "__main__":
    main()
