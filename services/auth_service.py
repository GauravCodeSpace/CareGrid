"""
CareGrid AI — Authentication Service
=======================================
Business-logic layer for user authentication and management.
Interacts with the User ORM model and uses bcrypt hashing.

Usage:
    from services.auth_service import AuthService

    user = AuthService.authenticate("admin", "admin123")
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from config.constants import UserRole
from models.database import get_db_session
from models.schema import User
from utils.auth import hash_password, verify_password

logger = logging.getLogger(__name__)


class AuthService:
    """
    Static service class for user authentication and CRUD operations.
    All methods open and close their own database sessions.
    """

    # ── Authentication ──────────────────────────────────────────

    @staticmethod
    def authenticate(username: str, password: str) -> Optional[dict]:
        """
        Authenticate a user by username and password.

        Args:
            username: Login username.
            password: Plaintext password.

        Returns:
            User dict on success, None on failure.
        """
        try:
            with get_db_session() as session:
                user: Optional[User] = (
                    session.query(User)
                    .filter(User.username == username, User.is_active == True)  # noqa: E712
                    .first()
                )
                if user is None:
                    logger.warning("Auth failed: user '%s' not found.", username)
                    return None

                if not verify_password(password, user.password_hash):
                    logger.warning("Auth failed: bad password for '%s'.", username)
                    return None

                logger.info("Auth success: user '%s' (role=%s).", username, user.role)
                return _user_to_dict(user)
        except Exception as exc:
            logger.error("Auth error for '%s': %s", username, exc)
            return None

    # ── Lookup ──────────────────────────────────────────────────

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[dict]:
        """
        Retrieve a user by primary key.

        Args:
            user_id: User ID.

        Returns:
            User dict or None.
        """
        try:
            with get_db_session() as session:
                user: Optional[User] = session.get(User, user_id)
                if user is None:
                    return None
                return _user_to_dict(user)
        except Exception as exc:
            logger.error("get_user_by_id(%d) error: %s", user_id, exc)
            return None

    # ── Create ──────────────────────────────────────────────────

    @staticmethod
    def create_user(
        username: str,
        password: str,
        role: str,
        full_name: str,
        email: Optional[str] = None,
        facility_id: Optional[int] = None,
    ) -> User:
        """
        Create a new user with hashed password.

        Args:
            username: Unique login name.
            password: Plaintext password (will be hashed).
            role: One of the UserRole values.
            full_name: Display name.
            email: Optional email address.
            facility_id: Optional linked facility ID.

        Returns:
            The created User ORM instance.

        Raises:
            Exception: On duplicate username or database error.
        """
        hashed = hash_password(password)
        with get_db_session() as session:
            user = User(
                username=username,
                password_hash=hashed,
                role=UserRole(role),
                full_name=full_name,
                email=email,
                facility_id=facility_id,
                is_active=True,
                created_at=datetime.utcnow(),
            )
            session.add(user)
            session.flush()  # Populate user.id before commit
            logger.info("Created user '%s' (id=%d, role=%s).", username, user.id, role)
            return user

    # ── Update password ─────────────────────────────────────────

    @staticmethod
    def update_password(user_id: int, new_password: str) -> bool:
        """
        Update a user's password.

        Args:
            user_id: Target user ID.
            new_password: New plaintext password.

        Returns:
            True on success, False on failure.
        """
        try:
            with get_db_session() as session:
                user: Optional[User] = session.get(User, user_id)
                if user is None:
                    logger.warning("update_password: user %d not found.", user_id)
                    return False
                user.password_hash = hash_password(new_password)
                logger.info("Password updated for user %d.", user_id)
                return True
        except Exception as exc:
            logger.error("update_password(%d) error: %s", user_id, exc)
            return False

    # ── List all ────────────────────────────────────────────────

    @staticmethod
    def get_all_users() -> list[dict]:
        """
        Retrieve all active users.

        Returns:
            List of user dicts (never includes password hashes).
        """
        try:
            with get_db_session() as session:
                users = (
                    session.query(User)
                    .filter(User.is_active == True)  # noqa: E712
                    .order_by(User.id)
                    .all()
                )
                return [_user_to_dict(u) for u in users]
        except Exception as exc:
            logger.error("get_all_users error: %s", exc)
            return []


# ── Private helpers ─────────────────────────────────────────────

def _user_to_dict(user: User) -> dict:
    """
    Convert a User ORM instance to a plain dictionary.
    Password hash is intentionally excluded.
    """
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role.value if isinstance(user.role, UserRole) else str(user.role),
        "full_name": user.full_name,
        "email": user.email,
        "facility_id": user.facility_id,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
