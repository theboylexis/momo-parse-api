"""
Database engine setup.

Reads DATABASE_URL from the environment:
  - If set → use it (PostgreSQL in production)
  - If unset → use SQLite file for local dev

Call init_db() once at app startup to create tables and enable DB-backed
storage in enricher/jobs.py and categorizer/counterparty.py.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()

_engine = None
_SessionLocal: Optional[sessionmaker] = None


def init_db() -> None:
    """Create the engine, session factory, and tables. Safe to call multiple times."""
    global _engine, _SessionLocal

    if _engine is not None:
        return  # already initialized

    url = os.getenv("DATABASE_URL")
    if not url:
        # Local dev fallback
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "momoparse.db")
        url = f"sqlite:///{db_path}"
        logger.info("DATABASE_URL not set — using SQLite at %s", db_path)
    else:
        logger.info("Connecting to database")

    _engine = create_engine(url, pool_pre_ping=True)
    _SessionLocal = sessionmaker(bind=_engine)

    # Import models so Base.metadata knows about them, then create tables
    import db.models  # noqa: F401

    Base.metadata.create_all(_engine)
    logger.info("Database tables ready")

    # Enable DB-backed storage in dependent modules
    from categorizer import counterparty
    from enricher import jobs

    jobs.enable_db()
    counterparty.enable_db()


def get_session() -> Session:
    """Return a new SQLAlchemy session. Caller must close it."""
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized — call init_db() first")
    return _SessionLocal()
