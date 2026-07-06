"""PostgreSQL connection and SQLAlchemy session management."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


def create_database_engine(database_url: str | None = None) -> Engine:
    url = database_url or settings.DATABASE_URL
    if not url:
        raise RuntimeError("DATABASE_URL 未配置")
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True,
    )


engine = create_database_engine() if settings.DATABASE_URL else None
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that owns one transaction scope per request."""
    if engine is None:
        raise RuntimeError("DATABASE_URL 未配置")
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def database_status(database_engine: Engine | None = None) -> dict[str, object]:
    """Verify connectivity and report non-sensitive schema information."""
    target = database_engine or engine
    if target is None:
        raise RuntimeError("DATABASE_URL 未配置")
    with target.connect() as connection:
        connection.execute(text("SELECT 1")).scalar_one()
    schema = "public" if target.dialect.name == "postgresql" else None
    table_names = inspect(target).get_table_names(schema=schema)
    return {
        "status": "ok",
        "database": target.url.database or "",
        "schema": schema or "main",
        "table_count": len(table_names),
    }
