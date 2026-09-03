"""Postgres schema for the CCA processed layer and raw-submission catalog.

Mirrors the spec's "Postgres schema" design: a single set of schemas shared
across all five Sectors via a `sector` column, never per-sector tables.

- `indices` — `runs` (one row per pipeline run, exactly one `is_current`)
  and `scores` (Sector Index and Dimension scores per district per run;
  `dimension IS NULL` marks a Sector Index row, per ADR-0003's Environment
  dimension-less path).
- `indicators` — `indicator_values`: cleaned, normalised indicator values
  *and* the raw value each was computed from, per district per indicator
  per run. A missing indicator for a district simply has no row
  (ADR-0007/ADR-0008: dropped, not imputed).
- `metadata` — `indicator_definitions`: the indicator catalog (sector,
  dimension, orientation, reference year, data-source attribution, an
  optional raw-unit label, and an optional NDP objective/target in raw
  units). Not part of ADR-0014's
  per-run append-only guarantee — it describes the catalog itself, not a
  scored run, so it's upserted in place.
  `districts`: the GRID3 district master list (ADR-0006), including the
  `is_urban` flag the dashboard's Urban annotation reads. Every
  `district_code` column elsewhere is foreign-keyed to this table, so a
  score or indicator value can't reference a district that isn't part of
  the master list (ADR-0007's closed-cohort rule enforced structurally,
  not just by the scoring engine's own validation).
- `catalog` — `submissions`: one row per raw submission (ADR-0012,
  ADR-0016): file location, submitter, timestamp, status, a validation
  report summary, and a path referencing the full report committed to the
  repo (ADR-0015).

Raw submission *files* never live here (ADR-0016) — only the numeric raw
*value* each Indicator carries does, alongside its normalised score
(ADR-0019).
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Engine,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    text,
)

metadata_obj = MetaData()

SCHEMAS = ("indices", "indicators", "metadata", "catalog")

runs = Table(
    "runs",
    metadata_obj,
    Column("run_id", Integer, primary_key=True, autoincrement=True),
    Column("computed_at", DateTime(timezone=True), nullable=False),
    Column("is_current", Boolean, nullable=False, default=False),
    # A Postgres partial unique index: at most one row may have is_current
    # = true, structurally enforcing the "exactly one current run" claim
    # above rather than leaving it to callers to get right (ADR-0014).
    Index(
        "uq_indices_runs_single_current",
        "is_current",
        unique=True,
        postgresql_where=text("is_current"),
    ),
    schema="indices",
)

scores = Table(
    "scores",
    metadata_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", Integer, ForeignKey("indices.runs.run_id"), nullable=False),
    Column("district_code", String, ForeignKey("metadata.districts.district_code"), nullable=False),
    Column("sector", String, nullable=False),
    Column("dimension", String, nullable=True),  # NULL = Sector Index row, not a Dimension row
    Column("score", Float, nullable=True),
    Column("complete", Boolean, nullable=False),
    Column("n_used", Integer, nullable=False),
    Column("n_total", Integer, nullable=False),
    schema="indices",
)

indicator_values = Table(
    "indicator_values",
    metadata_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", Integer, ForeignKey("indices.runs.run_id"), nullable=False),
    Column("district_code", String, ForeignKey("metadata.districts.district_code"), nullable=False),
    Column("indicator_id", String, nullable=False),
    Column("sector", String, nullable=False),
    Column("value", Float, nullable=False),
    # The value as submitted, before winsorize/orient/normalise -- stored
    # for display and raw-unit objective comparison only, never fed back
    # into scoring math (ADR-0019).
    Column("raw_value", Float, nullable=False),
    schema="indicators",
)

districts = Table(
    "districts",
    metadata_obj,
    Column("district_code", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("province", String, nullable=False),
    Column("province_code", String, nullable=False),
    # Not sourced from GRID3 (ADR-0006) -- callers supply this at write
    # time, per the spec's short list of mostly-urban districts (e.g.
    # Lusaka, Ndola) whose low Agriculture scores reflect land use, not
    # a capacity failure.
    Column("is_urban", Boolean, nullable=False, default=False),
    schema="metadata",
)

indicator_definitions = Table(
    "indicator_definitions",
    metadata_obj,
    Column("indicator_id", String, primary_key=True),
    Column("sector", String, nullable=False),
    Column("dimension", String, nullable=True),
    Column("orientation", String, nullable=False),
    Column("reference_year", Integer, nullable=True),
    Column("data_source", String, nullable=True),
    # The raw measure's unit label (e.g. "per 10k", "%", "km"), shown beside
    # the raw value and on the compare-to-others chart's axis (ticket 07) --
    # nullable, since not every Indicator has a natural unit and the catalog
    # may not carry one yet.
    Column("unit", String, nullable=True),
    # A future NDP target in the Indicator's raw units, drawn as a line on
    # the compare-to-others chart -- nullable, empty until MoFNP supplies
    # values (ADR-0019).
    Column("objective", Float, nullable=True),
    schema="metadata",
)

submissions = Table(
    "submissions",
    metadata_obj,
    Column("submission_id", Integer, primary_key=True, autoincrement=True),
    Column("file_location", String, nullable=False),
    Column("submitter", String, nullable=False),
    Column("submitted_at", DateTime(timezone=True), nullable=False),
    Column("status", String, nullable=False),  # "pending" / "published" / "rejected"
    Column("validation_report_summary", Text, nullable=True),
    # Path to the versioned report committed to the repo (ADR-0015) -- the
    # catalog entry references it rather than only holding a free-text
    # summary, since GitHub Actions' own log retention isn't permanent.
    Column("validation_report_path", String, nullable=True),
    schema="catalog",
)


def create_all(engine: Engine) -> None:
    """Create the CCA schemas and tables if they don't already exist."""
    with engine.begin() as conn:
        for schema in SCHEMAS:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
    metadata_obj.create_all(engine)
