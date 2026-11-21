"""
CareGrid AI — Database Utilities
==================================
Convenience functions for database operations used across services.

Usage:
    from utils.db import get_session, ensure_db_ready
"""

from models.database import get_db_session, init_db, check_db_health


def get_session():
    """
    Shortcut to get a database session context manager.

    Usage:
        with get_session() as session:
            results = session.query(Model).all()

    Returns:
        ContextManager[Session]: Database session.
    """
    return get_db_session()


def ensure_db_ready() -> bool:
    """
    Ensure the database is initialized and reachable.

    Returns:
        bool: True if database is ready, False otherwise.
    """
    try:
        init_db()
        return check_db_health()
    except Exception:
        return False
