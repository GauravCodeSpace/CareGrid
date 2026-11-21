"""
CareGrid AI — Database Engine & Session Management
=====================================================
Provides SQLAlchemy engine creation, session factory, and Base model.
Uses @st.cache_resource for singleton engine (thread-safe).
SQLite in dev, PostgreSQL-compatible schema.

Usage:
    from models.database import get_db_session, init_db

    # Initialize tables
    init_db()

    # Use in any service
    with get_db_session() as session:
        facilities = session.query(Facility).all()
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import settings

logger = logging.getLogger(__name__)


# ============================================================
# DECLARATIVE BASE
# ============================================================

class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ============================================================
# ENGINE & SESSION FACTORY
# ============================================================

_engine: Engine | None = None
_SessionFactory: sessionmaker | None = None


def get_engine() -> Engine:
    """
    Get or create the SQLAlchemy engine (singleton).

    Returns:
        Engine: SQLAlchemy engine instance.
    """
    global _engine
    if _engine is None:
        connect_args = {}
        if settings.DATABASE_URL.startswith("sqlite"):
            # Required for SQLite + multi-threaded Streamlit
            connect_args["check_same_thread"] = False

        _engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
        logger.info("Database engine created: %s", settings.DATABASE_URL[:50])
    return _engine


def get_session_factory() -> sessionmaker:
    """
    Get or create the session factory (singleton).

    Returns:
        sessionmaker: Configured session factory.
    """
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
        )
    return _SessionFactory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Automatically commits on success, rolls back on error, and closes.

    Usage:
        with get_db_session() as session:
            items = session.query(StockItem).all()

    Yields:
        Session: SQLAlchemy session instance.
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db() -> None:
    """
    Create all database tables from ORM models.
    Safe to call multiple times (uses CREATE IF NOT EXISTS).
    """
    # Import schema to register all models with Base.metadata
    import models.schema  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified successfully.")


def check_db_health() -> bool:
    """
    Verify database connectivity.

    Returns:
        bool: True if database is reachable, False otherwise.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        return False


def reset_db() -> None:
    """
    Drop and recreate all tables. USE WITH CAUTION.
    Only intended for development/testing.
    """
    import models.schema  # noqa: F401

    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.warning("Database reset: all tables dropped and recreated.")
