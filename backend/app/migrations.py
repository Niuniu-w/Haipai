from collections.abc import Callable

from sqlalchemy import Column, Connection, DateTime, Engine, MetaData, String, Table, func, select

from .database import Base

Migration = tuple[str, Callable[[Connection], None]]
metadata = MetaData()
schema_migrations = Table(
    "schema_migrations",
    metadata,
    Column("version", String(100), primary_key=True),
    Column("applied_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


def create_initial_schema(connection: Connection) -> None:
    Base.metadata.create_all(bind=connection)


MIGRATIONS: list[Migration] = [
    ("0001_initial_schema", create_initial_schema),
]


def run_migrations(engine: Engine) -> None:
    with engine.begin() as connection:
        metadata.create_all(bind=connection)
        applied = set(connection.scalars(select(schema_migrations.c.version)).all())
        for version, migration in MIGRATIONS:
            if version in applied:
                continue
            migration(connection)
            connection.execute(schema_migrations.insert().values(version=version))
