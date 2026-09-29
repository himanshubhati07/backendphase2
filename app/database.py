"""Synchronous SQLAlchemy database primitives."""
from __future__ import annotations

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def create_database_engine(database_url: str) -> Engine:
    """Create an engine for MySQL or SQLite, including SQLite FK enforcement."""
    # Accept the conventional mysql:// URL while pinning the pure-Python driver.
    if database_url.startswith("mysql://"):
        database_url = "mysql+pymysql://" + database_url.removeprefix("mysql://")
    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(database_url, future=True, pool_pre_ping=True, connect_args=connect_args)
    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def initialize_schema(engine: Engine) -> None:
    """Create tables for local development. Production schema changes use migrations."""
    from . import models  # noqa: F401 - registers model metadata
    Base.metadata.create_all(engine)
