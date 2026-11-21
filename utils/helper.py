"""
CareGrid AI — Helper Utilities
=================================
General-purpose formatting, HTML generation, and validation helpers
used across the Streamlit UI and services.

Usage:
    from utils.helper import format_number, kpi_card_html, validate_email
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional, Union

from config.constants import Colors


# ============================================================
# NUMBER & DATE FORMATTING
# ============================================================

def format_number(n: Union[int, float, None]) -> str:
    """
    Format a number with comma separators.

    Examples:
        >>> format_number(1234)
        '1,234'
        >>> format_number(1234567.89)
        '1,234,567.89'
        >>> format_number(None)
        '0'
    """
    if n is None:
        return "0"
    if isinstance(n, float):
        # Preserve up to 2 decimal places, drop trailing zeros
        formatted = f"{n:,.2f}".rstrip("0").rstrip(".")
        return formatted
    return f"{n:,}"


def format_percentage(value: Union[int, float], total: Union[int, float]) -> str:
    """
    Calculate percentage and return formatted string.

    Args:
        value: Numerator.
        total: Denominator.

    Returns:
        Formatted percentage string, e.g. "85.5%".
        Returns "0%" if total is zero.
    """
    if total == 0:
        return "0%"
    pct = (value / total) * 100
    return f"{pct:.1f}%"


def format_date(dt: Optional[Union[date, datetime]]) -> str:
    """
    Format a date into a human-readable string.

    Args:
        dt: A date or datetime object.

    Returns:
        Formatted string like "08 Jul 2026" or "—" if None.
    """
    if dt is None:
        return "—"
    if isinstance(dt, datetime):
        dt = dt.date()
    return dt.strftime("%d %b %Y")


def format_datetime(dt: Optional[datetime]) -> str:
    """
    Format a datetime into a human-readable string with time.

    Args:
        dt: A datetime object.

    Returns:
        Formatted string like "08 Jul 2026 · 14:30" or "—" if None.
    """
    if dt is None:
        return "—"
    return dt.strftime("%d %b %Y · %H:%M")


def get_date_range(days_back: int) -> tuple[date, date]:
    """
    Get a date range ending today.

    Args:
        days_back: Number of days to go back from today.

    Returns:
        Tuple of (start_date, end_date).
    """
    end = date.today()
    start = end - timedelta(days=days_back)
    return (start, end)


# ============================================================
# HTML BADGE & CARD GENERATORS
# ============================================================

def status_badge_html(status: str) -> str:
    """
    Generate a styled HTML badge for a status value.

    Colour mapping:
        - present, available, operational, active → green
        - absent, unavailable, out_of_order       → red
        - leave, half_day, maintenance             → amber
        - everything else                          → gray

    Args:
        status: Status string.

    Returns:
        HTML span string.
    """
    status_lower = status.lower().replace(" ", "_")
    color_map = {
        "present": Colors.SUCCESS,
        "available": Colors.SUCCESS,
        "operational": Colors.SUCCESS,
        "active": Colors.SUCCESS,
        "resolved": Colors.SUCCESS,
        "absent": Colors.DANGER,
        "unavailable": Colors.DANGER,
        "out_of_order": Colors.DANGER,
        "critical": Colors.DANGER,
        "leave": Colors.WARNING,
        "half_day": Colors.WARNING,
        "maintenance": Colors.WARNING,
        "warning": Colors.WARNING,
        "low": Colors.WARNING,
    }
    bg = color_map.get(status_lower, Colors.TEXT_SECONDARY)
    return (
        f'<span style="'
        f"background:{bg}; color:#fff; padding:2px 10px; "
        f"border-radius:12px; font-size:0.78rem; font-weight:600; "
        f"letter-spacing:0.3px;"
        f'">{status}</span>'
    )


def alert_card_html(
    icon: str,
    title: str,
    message: str,
    severity: str,
    time_str: str,
) -> str:
    """
    Generate a styled alert card HTML block.

    Args:
        icon: Emoji icon for the alert.
        title: Alert title/heading.
        message: Alert description text.
        severity: One of "critical", "warning", "info".
        time_str: Human-readable timestamp.

    Returns:
        HTML div string.
    """
    severity_lower = severity.lower()
    border_color = {
        "critical": Colors.DANGER,
        "warning": Colors.WARNING,
        "info": Colors.PRIMARY,
    }.get(severity_lower, Colors.TEXT_SECONDARY)

    bg_color = {
        "critical": "#FEF2F2",
        "warning": "#FFFBEB",
        "info": "#EFF6FF",
    }.get(severity_lower, "#F8FAFC")

    return (
        f'<div style="'
        f"border-left:4px solid {border_color}; background:{bg_color}; "
        f"padding:14px 18px; border-radius:8px; margin-bottom:10px;"
        f'">'
        f'<div style="display:flex; justify-content:space-between; align-items:center;">'
        f'<span style="font-size:1.05rem; font-weight:700;">{icon} {title}</span>'
        f'<span style="font-size:0.75rem; color:{Colors.TEXT_SECONDARY};">{time_str}</span>'
        f"</div>"
        f'<p style="margin:6px 0 0; font-size:0.88rem; color:{Colors.TEXT_PRIMARY};">'
        f"{message}</p>"
        f"</div>"
    )


def kpi_card_html(
    icon: str,
    label: str,
    value: str,
    delta: Optional[str] = None,
    delta_positive: bool = True,
) -> str:
    """
    Generate a styled KPI metric card HTML block.

    Args:
        icon: Emoji icon for the metric.
        label: KPI label text.
        value: Formatted KPI value.
        delta: Optional delta/change string (e.g. "+5.2%").
        delta_positive: Whether the delta is a positive change.

    Returns:
        HTML div string.
    """
    delta_html = ""
    if delta is not None:
        delta_color = Colors.SUCCESS if delta_positive else Colors.DANGER
        arrow = "↑" if delta_positive else "↓"
        delta_html = (
            f'<span style="font-size:0.78rem; color:{delta_color}; '
            f'font-weight:600; margin-left:8px;">{arrow} {delta}</span>'
        )

    return (
        f'<div style="'
        f"background:{Colors.SURFACE}; border:1px solid {Colors.BORDER}; "
        f"border-radius:12px; padding:20px; text-align:center; "
        f"box-shadow:0 1px 3px rgba(0,0,0,.06);"
        f'">'
        f'<div style="font-size:1.5rem; margin-bottom:4px;">{icon}</div>'
        f'<div style="font-size:0.8rem; color:{Colors.TEXT_SECONDARY}; '
        f'font-weight:500; text-transform:uppercase; letter-spacing:0.5px;">'
        f"{label}</div>"
        f'<div style="font-size:1.75rem; font-weight:800; color:{Colors.TEXT_PRIMARY}; '
        f'margin-top:4px;">{value}{delta_html}</div>'
        f"</div>"
    )


def section_header_html(icon: str, title: str) -> str:
    """
    Generate a styled section header HTML block.

    Args:
        icon: Emoji icon.
        title: Section title.

    Returns:
        HTML div string.
    """
    return (
        f'<div style="'
        f"display:flex; align-items:center; gap:10px; "
        f"padding:12px 0 8px; margin-top:18px; "
        f"border-bottom:2px solid {Colors.PRIMARY_LIGHT};"
        f'">'
        f'<span style="font-size:1.4rem;">{icon}</span>'
        f'<span style="font-size:1.15rem; font-weight:700; color:{Colors.TEXT_PRIMARY};">'
        f"{title}</span>"
        f"</div>"
    )


# ============================================================
# VALIDATION & TEXT UTILITIES
# ============================================================

_EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)


def validate_email(email: str) -> bool:
    """
    Validate an email address using a standard regex.

    Args:
        email: Email address string.

    Returns:
        True if the email matches a valid pattern.
    """
    if not email:
        return False
    return bool(_EMAIL_REGEX.match(email.strip()))


def truncate_text(text: str, max_length: int = 80) -> str:
    """
    Truncate text to a maximum length, appending ellipsis if shortened.

    Args:
        text: Input string.
        max_length: Maximum number of characters.

    Returns:
        Truncated string.
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


def calculate_percentage_change(
    old_val: Union[int, float],
    new_val: Union[int, float],
) -> float:
    """
    Calculate the percentage change between two values.

    Args:
        old_val: Previous/baseline value.
        new_val: Current value.

    Returns:
        Percentage change as a float (e.g. 15.5 for +15.5%).
        Returns 0.0 if old_val is zero.
    """
    if old_val == 0:
        return 0.0 if new_val == 0 else 100.0
    return round(((new_val - old_val) / abs(old_val)) * 100, 2)
