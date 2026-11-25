"""SQLAlchemy engine, session factory, and Base declarative class."""

from typing import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


settings = get_settings()

is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    """Enable foreign keys and WAL mode when using SQLite."""
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session per request and ensure cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema_migrations() -> None:
    """Safely add new columns to existing local databases without wiping stored data."""
    inspector = inspect(engine)
    if "feed_sources" not in inspector.get_table_names():
        return
    cols = {col["name"] for col in inspector.get_columns("feed_sources")}
    with engine.begin() as conn:
        if "region" not in cols:
            conn.execute(text("ALTER TABLE feed_sources ADD COLUMN region VARCHAR(20) NOT NULL DEFAULT 'global'"))
        if "source_type" not in cols:
            conn.execute(text("ALTER TABLE feed_sources ADD COLUMN source_type VARCHAR(30) NOT NULL DEFAULT 'rss'"))
