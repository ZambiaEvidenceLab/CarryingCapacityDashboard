"""Pure data-shaping helpers for the Dash app.

Every function here reshapes rows already computed by the scoring engine and
read from the processed Postgres layer (or the cached GRID3 boundaries) into
the shape a Plotly figure or Dash component expects. None of it aggregates,
normalises, or otherwise scores anything — that happens once, upstream, in
the pipeline (ADR-0010). Kept free of any Dash/Postgres import so it can be
tested with plain DataFrames.
"""

from __future__ import annotations

import pandas as pd
from shapely.geometry import shape

from cca.grid3.client import District
from cca.scoring.indicators import CCA_INDICATORS

URBAN_AGRICULTURE_ANNOTATION = (
    "This district is classified as mostly urban. Its lower Agriculture score "
    "reflects urban land use, not a failure of agricultural capacity."
)

# The Supply/Access segmented control's measures (ticket 05). "Overall" is the
# Sector Index (dimension IS NULL); "Supply"/"Access" name the Dimension rows
# verbatim (they double as the `indices.scores.dimension` value read back), so
# the domain vocabulary carries straight from the DB to the UI label.
OVERALL, SUPPLY, ACCESS = "Overall", "Supply", "Access"
MEASURES = [
    {"label": OVERALL, "value": OVERALL},
    {"label": SUPPLY, "value": SUPPLY},
    {"label": ACCESS, "value": ACCESS},
]
OVERALL_ONLY = [{"label": OVERALL, "value": OVERALL}]

# Sectors that actually have a Supply/Access split. Environment's Indicators
# have no Dimension (ADR-0003), so it never has Dimension scores to colour by —
# derived from the catalog rather than hard-coding "Environment" so a future
# dimension-less Sector is handled without a code change.
SECTORS_WITH_DIMENSIONS = frozenset(m.sector for m in CCA_INDICATORS if m.dimension is not None)


def effective_measure(sector: str, measure: str | None) -> str:
    """The measure actually shown, collapsing to Overall where a Dimension can't apply.

    A dimension-less Sector (Environment) has no Supply/Access scores, and a
    stale/blank measure is meaningless — either resolves to Overall so the map
    and list stay correct even mid-switch (the control is also reset for
    Environment, but this guards the data path independently).
    """
    if measure in (SUPPLY, ACCESS) and sector in SECTORS_WITH_DIMENSIONS:
        return measure
    return OVERALL


def indicator_label(indicator_id: str) -> str:
    """A readable Indicator label from its id (drops the Sector prefix, e.g.
    'health_doctor_to_population_ratio' -> 'Doctor to population ratio')."""
    _, _, rest = indicator_id.partition("_")
    body = rest or indicator_id
    return body.replace("_", " ").capitalize()


def sector_dimension_indicators(sector: str) -> dict[str, list[str]]:
    """The Sector's Indicator labels grouped by Dimension, for the 'what's in
    Supply / Access?' hover (ticket 05).

    A dimension-less Sector (Environment) comes back under a single `None` key
    so the hover can explain that its Indicators average directly, with no
    Supply/Access split.
    """
    grouped: dict[str, list[str]] = {}
    for meta in CCA_INDICATORS:
        if meta.sector == sector:
            grouped.setdefault(meta.dimension, []).append(indicator_label(meta.indicator_id))
    return grouped


def build_district_geojson(districts: list[District]) -> dict:
    """A GeoJSON FeatureCollection keyed by district_code, for the choropleth map."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": d.code,
                "properties": {"name": d.name, "province": d.province},
                "geometry": d.geometry,
            }
            for d in districts
        ],
    }


def build_district_points(districts: list[District]) -> dict[str, tuple[float, float]]:
    """One representative `(lon, lat)` point per District, for map overlay markers.

    Used by the map's Scattermap overlays (data-completeness signal and the
    selected-District highlight, ticket 04) — `Choroplethmap` colours fills
    but cannot draw a per-District hatch or ring, so those signals ride a
    point layer instead. `representative_point()` is guaranteed to fall
    inside the polygon (unlike a raw centroid, which can land outside a
    concave or multi-part District). Computed once at app startup on the
    already-simplified boundaries (ADR-0017), never per page load.
    """
    points: dict[str, tuple[float, float]] = {}
    for d in districts:
        point = shape(d.geometry).representative_point()
        points[d.code] = (point.x, point.y)
    return points


def shape_ranked_list(sector_scores: pd.DataFrame, districts: pd.DataFrame) -> list[dict]:
    """Scored Districts for one Sector, ranked worst-served first (ticket 04).

    Inner-joined to the Sector's scores (not left-joined like the map), so a
    District with no Sector Index yet simply doesn't appear in the ranking —
    the list ranks the Districts that actually have a score, cheapest budget
    question first. Ascending by Sector Index score: rank 1 is the most
    underserved. Each row carries the name, score, the Data-completeness flag
    (amber dot when the score used incomplete Indicators) and the Urban flag.
    """
    merged = sector_scores.merge(
        districts[["district_code", "name", "is_urban"]], on="district_code", how="inner"
    )
    merged = merged[merged["score"].notna()].sort_values("score", ascending=True)

    return [
        {
            "rank": rank,
            "district_code": row["district_code"],
            "name": row["name"],
            "score": float(row["score"]),
            "complete": bool(row["complete"]),
            "is_urban": bool(row["is_urban"]),
        }
        for rank, (_, row) in enumerate(merged.iterrows(), start=1)
    ]


def shape_map_data(sector_scores: pd.DataFrame, districts: pd.DataFrame) -> pd.DataFrame:
    """Merge district names/urban flag with one Sector's Index scores for the choropleth map.

    Left-joined from the district master list, not the scores, so a district
    with no scored row yet for this Sector still appears on the map (with a
    blank score and an "Incomplete data" label) rather than silently vanishing
    from the "all 116 districts" view.
    """
    merged = districts[["district_code", "name", "is_urban"]].merge(
        sector_scores, on="district_code", how="left"
    )
    merged["complete"] = merged["complete"].fillna(False)
    merged["completeness_label"] = merged["complete"].map({True: "Complete", False: "Incomplete data"})
    return merged


def score_range(scores: pd.DataFrame) -> tuple[float, float]:
    """The live min-max of a Sector's present scores, for map colour scaling (ADR-0017).

    Falls back to 0-100 when there's nothing to shade across yet (no scores,
    or every present score identical) — `zmin == zmax` would otherwise
    flatten the colourscale to a single shade.
    """
    present = scores["score"].dropna()
    if present.empty:
        return 0.0, 100.0
    lo, hi = float(present.min()), float(present.max())
    return (lo, hi) if hi > lo else (0.0, 100.0)


def shape_national_summary(summary: dict) -> dict:
    """Round the national summary strip's figures; an empty run/sector stays None."""

    def _round(value: float | int | None, ndigits: int = 1) -> float | None:
        return None if value is None or pd.isna(value) else round(float(value), ndigits)

    return {
        "average": _round(summary.get("average")),
        "spread": _round(summary.get("spread")),
        "incomplete_count": int(summary["incomplete_count"]) if summary.get("incomplete_count") is not None else 0,
    }


def shape_radar_data(district_code: str, all_sector_scores: pd.DataFrame, sectors: list[str]) -> dict:
    """A district's Sector Index scores against the national average, one entry per Sector.

    A Sector with no score yet for this district (or nationally) shows up as
    `None` rather than being dropped, so the radar chart's axes stay stable.
    """
    by_district = all_sector_scores[all_sector_scores["district_code"] == district_code].set_index("sector")
    national_average = all_sector_scores.groupby("sector")["score"].mean()

    district_scores: list[float | None] = []
    district_complete: list[bool] = []
    national_scores: list[float | None] = []
    for sector in sectors:
        if sector in by_district.index:
            row = by_district.loc[sector]
            district_scores.append(None if pd.isna(row["score"]) else float(row["score"]))
            district_complete.append(bool(row["complete"]))
        else:
            district_scores.append(None)
            district_complete.append(False)

        avg = national_average.get(sector)
        national_scores.append(None if avg is None or pd.isna(avg) else float(avg))

    return {
        "sectors": sectors,
        "district_scores": district_scores,
        "district_complete": district_complete,
        "national_average_scores": national_scores,
    }


def shape_decomposition(district_code: str, sector: str, breakdown: dict[str, pd.DataFrame]) -> dict:
    """Dimension and Indicator rows for one district's Decomposition View of one Sector.

    Environment has no Dimension rows (ADR-0003) — `dimensions` comes back
    empty in that case, and the UI falls back to showing Indicators directly.
    `sector_complete` flags whether the Sector Index used every Indicator, so a
    dimension-less Sector still carries a completeness signal (it has no
    Dimension rows to carry one). Defaults to True when the Sector Index row is
    absent (e.g. an unscored Sector for this district).
    """
    dimensions = breakdown["dimensions"]
    indicator_values = breakdown["indicator_values"]
    sector_index = breakdown.get("sector_index")

    sector_complete = True
    if sector_index is not None and not sector_index.empty:
        sector_complete = bool(sector_index.iloc[0]["complete"])

    return {
        "district_code": district_code,
        "sector": sector,
        "dimensions": dimensions.to_dict("records"),
        "indicators": indicator_values.to_dict("records"),
        "sector_complete": sector_complete,
    }


def is_urban_district(districts: pd.DataFrame, district_code: str) -> bool:
    """Whether a district is flagged mostly-urban (Urban annotation, CONTEXT.md)."""
    row = districts.loc[districts["district_code"] == district_code]
    return bool(row.iloc[0]["is_urban"]) if not row.empty else False
