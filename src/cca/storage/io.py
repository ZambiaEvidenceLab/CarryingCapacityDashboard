"""Read/write functions for the CCA processed layer and raw-submission catalog.

Wraps `cca.storage.schema`'s tables with the operations the data-loading
side (write) and the dashboard (read) actually need. Callers supply a
SQLAlchemy `Engine` built from their own connection string/credential —
this module holds no credentials itself, matching the spec's separate
read-only (dashboard) vs. data-loading credentials.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import Engine, text

from cca.grid3.client import District
from cca.scoring.engine import IndicatorMeta, ScoringResult

# Shared by every read function below: join a table to the one run flagged
# current (schema.py enforces there's at most one) rather than repeating
# this join inline in each query. Callers still add their own WHERE clause,
# including `r.is_current = true`.
_CURRENT_RUN_JOIN = "JOIN indices.runs r ON r.run_id = {alias}.run_id"


def write_district_master_list(
    engine: Engine,
    districts: list[District],
    *,
    urban_district_names: frozenset[str] = frozenset(),
) -> None:
    """Upsert the GRID3 district master list (ADR-0006), flagging mostly-urban districts.

    Must run before `write_scoring_run` — every `district_code` on the
    processed layer is foreign-keyed to this table (ADR-0007's closed
    cohort, enforced structurally). Like the GRID3 cache itself, districts
    are only ever added/removed/updated as a full refresh, never
    individually, so this simply reflects whatever the current master list
    is — it isn't part of ADR-0014's per-run append-only guarantee.
    """
    with engine.begin() as conn:
        for district in districts:
            conn.execute(
                text(
                    "INSERT INTO metadata.districts "
                    "(district_code, name, province, province_code, is_urban) "
                    "VALUES (:district_code, :name, :province, :province_code, :is_urban) "
                    "ON CONFLICT (district_code) DO UPDATE SET "
                    "name = EXCLUDED.name, province = EXCLUDED.province, "
                    "province_code = EXCLUDED.province_code, is_urban = EXCLUDED.is_urban"
                ),
                {
                    "district_code": district.code,
                    "name": district.name,
                    "province": district.province,
                    "province_code": district.province_code,
                    "is_urban": district.name in urban_district_names,
                },
            )


def read_districts(engine: Engine) -> pd.DataFrame:
    """The district master list, including the Urban annotation flag the dashboard reads."""
    with engine.connect() as conn:
        return pd.read_sql(
            text("SELECT district_code, name, province, province_code, is_urban FROM metadata.districts"),
            conn,
        )


def write_scoring_run(
    engine: Engine,
    result: ScoringResult,
    indicator_metas: list[IndicatorMeta],
    *,
    computed_at: datetime | None = None,
) -> int:
    """Persist a scoring-engine run as a new, current, append-only run (ADR-0014).

    Writes `indices.runs`, `indices.scores` (Dimension and Sector Index
    rows), and `indicators.indicator_values` (normalised and raw
    per-indicator values, ADR-0019 — a missing indicator for a district
    simply has no row, per ADR-0007/ADR-0008's "dropped, not imputed").
    Every prior run is marked `is_current = false`; the new run is marked
    `true`.

    Returns the new run's `run_id`.
    """
    if not result.validation.passed:
        raise ValueError(f"Cannot write a failed scoring run: {result.validation.reasons}")

    computed_at = computed_at or datetime.now(timezone.utc)
    meta_by_id = {m.indicator_id: m for m in indicator_metas}

    with engine.begin() as conn:
        conn.execute(text("UPDATE indices.runs SET is_current = false"))
        run_id = conn.execute(
            text(
                "INSERT INTO indices.runs (computed_at, is_current) "
                "VALUES (:computed_at, true) RETURNING run_id"
            ),
            {"computed_at": computed_at},
        ).scalar_one()

        scores = pd.concat([result.dimension_scores, result.sector_scores], ignore_index=True)
        scores.insert(0, "run_id", run_id)
        scores.to_sql("scores", conn, schema="indices", if_exists="append", index=False)

        value_records = [
            {
                "run_id": run_id,
                "district_code": district_code,
                "indicator_id": indicator_id,
                "sector": meta_by_id[indicator_id].sector,
                "value": float(value),
                "raw_value": float(indicator_score.raw[district_code]),
            }
            for indicator_id, indicator_score in result.indicator_scores.items()
            for district_code, value in indicator_score.normalised.items()
            if pd.notna(value)
        ]
        value_columns = ["run_id", "district_code", "indicator_id", "sector", "value", "raw_value"]
        pd.DataFrame(value_records, columns=value_columns).to_sql(
            "indicator_values", conn, schema="indicators", if_exists="append", index=False
        )

    return run_id


def write_indicator_metadata(
    engine: Engine,
    indicator_metas: list[IndicatorMeta],
    *,
    reference_years: dict[str, int] | None = None,
    data_sources: dict[str, str] | None = None,
    objectives: dict[str, float] | None = None,
) -> None:
    """Upsert the indicator catalog's definitions, reference years, data-source attribution,
    and NDP objectives (ADR-0019 — nullable, empty until MoFNP supplies values).

    Unlike the processed layer, this describes the catalog itself rather
    than a scored run, so it isn't part of ADR-0014's append-only
    guarantee — re-running this replaces each indicator's row in place.
    """
    reference_years = reference_years or {}
    data_sources = data_sources or {}
    objectives = objectives or {}

    with engine.begin() as conn:
        for meta in indicator_metas:
            conn.execute(
                text(
                    "INSERT INTO metadata.indicator_definitions "
                    "(indicator_id, sector, dimension, orientation, reference_year, data_source, objective) "
                    "VALUES (:indicator_id, :sector, :dimension, :orientation, :reference_year, "
                    ":data_source, :objective) "
                    "ON CONFLICT (indicator_id) DO UPDATE SET "
                    "sector = EXCLUDED.sector, dimension = EXCLUDED.dimension, "
                    "orientation = EXCLUDED.orientation, reference_year = EXCLUDED.reference_year, "
                    "data_source = EXCLUDED.data_source, objective = EXCLUDED.objective"
                ),
                {
                    "indicator_id": meta.indicator_id,
                    "sector": meta.sector,
                    "dimension": meta.dimension,
                    "orientation": meta.orientation,
                    "reference_year": reference_years.get(meta.indicator_id),
                    "data_source": data_sources.get(meta.indicator_id),
                    "objective": objectives.get(meta.indicator_id),
                },
            )


def read_latest_sector_scores(engine: Engine, sector: str | None = None) -> pd.DataFrame:
    """Sector Index scores from the current run, ready for the landing-page map (ADR-0010)."""
    query = (
        "SELECT s.district_code, s.sector, s.score, s.complete, s.n_used, s.n_total "
        f"FROM indices.scores s {_CURRENT_RUN_JOIN.format(alias='s')} "
        "WHERE r.is_current = true AND s.dimension IS NULL"
    )
    params: dict[str, str] = {}
    if sector is not None:
        query += " AND s.sector = :sector"
        params["sector"] = sector

    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)


def read_latest_dimension_scores(engine: Engine, sector: str, dimension: str) -> pd.DataFrame:
    """One Dimension's (Supply/Access) scores for a Sector from the current run (ADR-0010).

    Same shape as `read_latest_sector_scores`, but the Dimension rows
    (`dimension = 'Supply' | 'Access'`) rather than the Sector Index row
    (`dimension IS NULL`) — so the map/list can recolour and re-rank to a
    Dimension without re-deriving anything (ticket 05). Environment has no
    Dimension rows (ADR-0003), so this comes back empty for it; callers force
    Overall for the dimension-less Sector rather than querying here.
    """
    query = (
        "SELECT s.district_code, s.sector, s.score, s.complete, s.n_used, s.n_total "
        f"FROM indices.scores s {_CURRENT_RUN_JOIN.format(alias='s')} "
        "WHERE r.is_current = true AND s.sector = :sector AND s.dimension = :dimension"
    )
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params={"sector": sector, "dimension": dimension})


def read_district_decomposition(engine: Engine, district_code: str, sector: str) -> dict[str, pd.DataFrame]:
    """Dimension and Indicator scores behind one district's current Sector Index (Decomposition View).

    Also returns the Sector Index row itself (`sector_index`, the `dimension IS
    NULL` score) so the drawer can flag an incomplete Sector Index even for a
    dimension-less Sector (Environment, ADR-0003), which has no Dimension rows to
    carry the completeness signal.
    """
    with engine.connect() as conn:
        dimensions = pd.read_sql(
            text(
                "SELECT s.dimension, s.score, s.complete, s.n_used, s.n_total "
                f"FROM indices.scores s {_CURRENT_RUN_JOIN.format(alias='s')} "
                "WHERE r.is_current = true AND s.district_code = :district_code "
                "AND s.sector = :sector AND s.dimension IS NOT NULL"
            ),
            conn,
            params={"district_code": district_code, "sector": sector},
        )
        sector_index = pd.read_sql(
            text(
                "SELECT s.score, s.complete, s.n_used, s.n_total "
                f"FROM indices.scores s {_CURRENT_RUN_JOIN.format(alias='s')} "
                "WHERE r.is_current = true AND s.district_code = :district_code "
                "AND s.sector = :sector AND s.dimension IS NULL"
            ),
            conn,
            params={"district_code": district_code, "sector": sector},
        )
        indicator_values = pd.read_sql(
            text(
                "SELECT v.indicator_id, v.value, v.raw_value, m.dimension, m.reference_year, "
                "m.data_source, m.objective "
                "FROM indicators.indicator_values v "
                f"{_CURRENT_RUN_JOIN.format(alias='v')} "
                "LEFT JOIN metadata.indicator_definitions m ON m.indicator_id = v.indicator_id "
                "WHERE r.is_current = true AND v.district_code = :district_code AND v.sector = :sector"
            ),
            conn,
            params={"district_code": district_code, "sector": sector},
        )
    return {"dimensions": dimensions, "indicator_values": indicator_values, "sector_index": sector_index}


def read_indicator_cohort_values(engine: Engine, indicator_id: str) -> pd.DataFrame:
    """One Indicator's raw value for every District in the current run (compare-to-others chart).

    A District with no value for this Indicator simply has no row
    (ADR-0007/ADR-0008: dropped, not imputed) — callers reindex against the
    district master list themselves if they need to render "no value
    reported" for the rest of the cohort.
    """
    with engine.connect() as conn:
        return pd.read_sql(
            text(
                "SELECT v.district_code, v.raw_value "
                "FROM indicators.indicator_values v "
                f"{_CURRENT_RUN_JOIN.format(alias='v')} "
                "WHERE r.is_current = true AND v.indicator_id = :indicator_id"
            ),
            conn,
            params={"indicator_id": indicator_id},
        )


def read_national_summary(engine: Engine, sector: str) -> dict[str, float | int | None]:
    """National summary strip for one Sector: average score, spread, and low-completeness count."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT AVG(s.score) AS average, STDDEV_POP(s.score) AS spread, "
                "COUNT(*) FILTER (WHERE NOT s.complete) AS incomplete_count "
                f"FROM indices.scores s {_CURRENT_RUN_JOIN.format(alias='s')} "
                "WHERE r.is_current = true AND s.sector = :sector AND s.dimension IS NULL"
            ),
            {"sector": sector},
        ).mappings().one()
    return dict(row)


def read_indicator_catalog(engine: Engine) -> pd.DataFrame:
    """The indicator catalog (sector, dimension, orientation, reference year, source).

    Used by the dashboard's Methodology FAQ (ADR-0010) — not tied to any one
    district or run, since it describes the catalog itself.
    """
    with engine.connect() as conn:
        return pd.read_sql(
            text(
                "SELECT indicator_id, sector, dimension, orientation, reference_year, data_source, objective "
                "FROM metadata.indicator_definitions"
            ),
            conn,
        )


def write_submission(
    engine: Engine,
    *,
    file_location: str,
    submitter: str,
    submitted_at: datetime | None = None,
    status: str = "pending",
    validation_report_summary: str | None = None,
    validation_report_path: str | None = None,
) -> int:
    """Record a new raw submission in the catalog (ADR-0012). Returns the `submission_id`."""
    submitted_at = submitted_at or datetime.now(timezone.utc)
    with engine.begin() as conn:
        return conn.execute(
            text(
                "INSERT INTO catalog.submissions "
                "(file_location, submitter, submitted_at, status, "
                "validation_report_summary, validation_report_path) "
                "VALUES (:file_location, :submitter, :submitted_at, :status, "
                ":validation_report_summary, :validation_report_path) "
                "RETURNING submission_id"
            ),
            {
                "file_location": file_location,
                "submitter": submitter,
                "submitted_at": submitted_at,
                "status": status,
                "validation_report_summary": validation_report_summary,
                "validation_report_path": validation_report_path,
            },
        ).scalar_one()


def update_submission_status(
    engine: Engine,
    submission_id: int,
    status: str,
    *,
    validation_report_summary: str | None = None,
    validation_report_path: str | None = None,
) -> None:
    """Promote/reject a submission (ADR-0012). The raw file itself is never touched (ADR-0016)."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE catalog.submissions SET status = :status, "
                "validation_report_summary = COALESCE(:validation_report_summary, validation_report_summary), "
                "validation_report_path = COALESCE(:validation_report_path, validation_report_path) "
                "WHERE submission_id = :submission_id"
            ),
            {
                "status": status,
                "validation_report_summary": validation_report_summary,
                "validation_report_path": validation_report_path,
                "submission_id": submission_id,
            },
        )
