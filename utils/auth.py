"""
CareGrid AI — Authentication Utilities
=========================================
Password hashing, session management, and access-control helpers
for the Streamlit front-end.

Usage:
    from utils.auth import hash_password, verify_password, is_authenticated
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Optional

import bcrypt
import streamlit as st


# ============================================================
# PASSWORD HASHING
# ============================================================

def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        password: Plaintext password string.

    Returns:
        Bcrypt hash string (UTF-8 encoded).
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.

    Args:
        password: Plaintext password to check.
        hashed: Bcrypt hash to compare against.

    Returns:
        True if the password matches.
    """
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            hashed.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


import json
from streamlit_cookies_controller import CookieController

# Initialize cookie controller
_cookie_controller = None

def get_cookie_controller():
    global _cookie_controller
    if _cookie_controller is None:
        _cookie_controller = CookieController()
    return _cookie_controller


# ============================================================
# SESSION STATE MANAGEMENT
# ============================================================

_AUTH_KEYS = (
    "authenticated",
    "user",
    "user_role",
    "user_facility_id",
)


def login_user(session_state: Any, user_dict: dict) -> None:
    """
    Persist authentication data in Streamlit session state and cookie.
    """
    session_state["authenticated"] = True
    session_state["user"] = user_dict
    session_state["user_role"] = user_dict.get("role", "")
    session_state["user_facility_id"] = user_dict.get("facility_id")
    
    # Persist via cookie
    try:
        ctrl = get_cookie_controller()
        ctrl.set("cg_auth", json.dumps(user_dict), path="/")
    except Exception:
        pass


def logout_user(session_state: Any) -> None:
    """
    Clear all authentication keys from Streamlit session state and cookie.
    """
    for key in _AUTH_KEYS:
        session_state.pop(key, None)
    
    try:
        ctrl = get_cookie_controller()
        ctrl.remove("cg_auth")
    except Exception:
        pass


def is_authenticated() -> bool:
    """
    Check whether the current Streamlit session is authenticated.
    Also checks cookies if session state is empty.
    """
    if st.session_state.get("authenticated", False) is True:
        return True
        
    # Check cookie fallback
    try:
        ctrl = get_cookie_controller()
        auth_cookie = ctrl.get("cg_auth")
        if auth_cookie:
            if isinstance(auth_cookie, str):
                user_dict = json.loads(auth_cookie)
            else:
                user_dict = auth_cookie
                
            # Restore session state
            st.session_state["authenticated"] = True
            st.session_state["user"] = user_dict
            st.session_state["user_role"] = user_dict.get("role", "")
            st.session_state["user_facility_id"] = user_dict.get("facility_id")
            return True
    except Exception:
        pass
        
    return False


def get_current_user() -> Optional[dict]:
    """
    Retrieve the current user dict from session state.
    """
    if is_authenticated():
        return st.session_state.get("user")
    return None


def require_auth() -> bool:
    """
    Guard function that displays an error and stops execution if
    the user is not authenticated.

    Usage:
        if not require_auth():
            st.stop()

    Returns:
        True if authenticated, False otherwise (after showing error).
    """
    if not is_authenticated():
        st.error("🔐 Please log in to access this page.")
        return False
    return True


def require_role(role: str) -> bool:
    """
    Check if the current user has the required role.

    Displays a warning and returns False when the role does not match.
    System Administrators are granted access to all roles.

    Args:
        role: Required role string (e.g. ``"District Administrator"``).

    Returns:
        True if the user has the required role.
    """
    if not is_authenticated():
        st.error("🔐 Please log in to access this page.")
        return False

    user = get_current_user()
    if user is None:
        st.error("🔐 Session expired. Please log in again.")
        return False

    current_role = user.get("role", "")

    # System Administrators have unrestricted access
    if current_role == "System Administrator":
        return True

    if current_role != role:
        st.warning(
            f"⚠️ Access denied. This page requires the **{role}** role. "
            f"Your role is **{current_role}**."
        )
        return False

    return True
