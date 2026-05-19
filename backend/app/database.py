"""Database configuration for the Care Plan Generator MVP."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://careplan:careplan@localhost:5432/careplan",
)

# SQLite support is only a fallback convenience; Docker Compose uses PostgreSQL.
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db() -> None:
    """Create database tables for the Day 3 learning MVP.

    TODO: Replace create_all with Alembic migrations before production use so
    schema changes are reviewed, versioned, reversible, and safe for real data.
    create_all creates missing tables, but it does not migrate existing tables.
    """
    Base.metadata.create_all(bind=engine)


def get_db():
    """Yield one SQLAlchemy session per request and always close it afterward.

    FastAPI runs the code after `yield` once the route finishes, which keeps
    session cleanup centralized instead of requiring every route to close it.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
