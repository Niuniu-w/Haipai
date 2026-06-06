from sqlalchemy import create_engine

from backend.app import models  # noqa: F401
from backend.app.migrations import run_migrations


def test_migrations_are_recorded_and_idempotent() -> None:
    engine = create_engine("sqlite://")

    run_migrations(engine)
    run_migrations(engine)

    with engine.connect() as connection:
        versions = connection.exec_driver_sql("SELECT version FROM schema_migrations").fetchall()
        tables = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert versions == [("0001_initial_schema",)]
    assert "projects" in tables
