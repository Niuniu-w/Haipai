import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


default_database = Path(__file__).resolve().parents[1] / "storyforge.db"
database_url = os.getenv("STORYFORGE_DATABASE_URL", f"sqlite:///{default_database}")

engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def init_database() -> None:
    from . import models  # noqa: F401
    from .migrations import run_migrations

    run_migrations(engine)
