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

from cca.grid3.client import District

URBAN_AGRICULTURE_ANNOTATION = (
    "This district is classified as mostly urban. Its lower Agriculture score "
    "reflects urban land use, not a failure of agricultural capacity."
)


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
    """
    dimensions = breakdown["dimensions"]
    indicator_values = breakdown["indicator_values"]

    return {
        "district_code": district_code,
        "sector": sector,
        "dimensions": dimensions.to_dict("records"),
        "indicators": indicator_values.to_dict("records"),
    }


def is_urban_district(districts: pd.DataFrame, district_code: str) -> bool:
    """Whether a district is flagged mostly-urban (Urban annotation, CONTEXT.md)."""
    row = districts.loc[districts["district_code"] == district_code]
    return bool(row.iloc[0]["is_urban"]) if not row.empty else False
