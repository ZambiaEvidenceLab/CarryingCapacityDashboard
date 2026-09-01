import os

import pytest
from sqlalchemy import create_engine, text

from cca.storage.schema import create_all

DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg://cca_dev:cca_dev_local_only@localhost:5432/cca_test"

TABLES_TO_TRUNCATE = (
    "catalog.submissions",
    "indicators.indicator_values",
    "indices.scores",
    "indices.runs",
    "metadata.indicator_definitions",
    "metadata.districts",
)


@pytest.fixture(scope="session")
def pg_engine():
    """A SQLAlchemy engine against a local Postgres test database (schema ticket, ADR-0016).

    Skips the whole session's Postgres-backed tests if nothing is reachable
    at `CCA_TEST_DATABASE_URL` (or the local dev default) — these are
    adapter-level integration tests, not something every environment is
    expected to run.
    """
    database_url = os.environ.get("CCA_TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    engine = create_engine(database_url)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"No Postgres test database reachable at {database_url!r}: {exc}")

    create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def clean_pg(pg_engine):
    """Truncate the CCA tables before each test so Postgres-backed tests stay isolated."""
    with pg_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(TABLES_TO_TRUNCATE)} RESTART IDENTITY CASCADE"))
    return pg_engine
