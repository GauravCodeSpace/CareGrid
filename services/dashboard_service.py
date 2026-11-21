"""
CareGrid AI — Dashboard Service
==================================
Aggregation service for the main dashboard.
Provides KPI summaries, facility health scores, alert feeds, and trend data.

Usage:
    from services.dashboard_service import DashboardService
    kpis = DashboardService.get_kpi_summary()
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import func, case

from models.database import get_db_session
from models.schema import (
    Alert,
    BedStatus,
    DoctorAttendance,
    Facility,
    Footfall,
    StockItem,
    TestAvailability,
)
from config.constants import AttendanceStatus, AlertSeverity

logger = logging.getLogger(__name__)


class DashboardService:
    """Static service that drives the main dashboard."""

    # ── KPI Summary ──────────────────────────────────────────
    @staticmethod
    def get_kpi_summary() -> dict[str, Any]:
        """
        Compute top-level KPI metrics for the dashboard header.

        Returns:
            dict with keys: total_facilities, active_alerts,
            low_stock_items, avg_bed_occupancy_pct, avg_attendance_pct.
        """
        with get_db_session() as session:
            total_facilities = session.query(func.count(Facility.id)).scalar() or 0

            active_alerts = (
                session.query(func.count(Alert.id))
                .filter(Alert.is_resolved == False)  # noqa: E712
                .scalar()
                or 0
            )

            low_stock_items = (
                session.query(func.count(StockItem.id))
                .filter(StockItem.current_stock < StockItem.reorder_level)
                .scalar()
                or 0
            )

            # Bed occupancy: aggregate across all facilities
            bed_data = session.query(
                func.sum(BedStatus.occupied_beds),
                func.sum(BedStatus.total_beds),
            ).first()
            total_occupied = bed_data[0] or 0
            total_beds = bed_data[1] or 1  # avoid div-by-zero
            avg_bed_occupancy_pct = round((total_occupied / total_beds) * 100, 1)

            # Attendance percentage (last 30 days)
            cutoff = date.today() - timedelta(days=30)
            total_attendance = (
                session.query(func.count(DoctorAttendance.id))
                .filter(DoctorAttendance.date >= cutoff)
                .scalar()
                or 0
            )
            present_count = (
                session.query(func.count(DoctorAttendance.id))
                .filter(
                    DoctorAttendance.date >= cutoff,
                    DoctorAttendance.status == AttendanceStatus.PRESENT,
                )
                .scalar()
                or 0
            )
            avg_attendance_pct = (
                round((present_count / total_attendance) * 100, 1)
                if total_attendance > 0
                else 0.0
            )

        return {
            "total_facilities": total_facilities,
            "active_alerts": active_alerts,
            "low_stock_items": low_stock_items,
            "avg_bed_occupancy_pct": avg_bed_occupancy_pct,
            "avg_attendance_pct": avg_attendance_pct,
        }

    # ── Facility Health Table ────────────────────────────────
    @staticmethod
    def get_facility_health_table() -> list[dict[str, Any]]:
        """
        Compute a health score for every facility.

        Health score (0-100, higher = healthier):
            stock_health × 0.30 + attendance × 0.25
            + bed_health × 0.25 + diagnostics × 0.20

        Returns:
            List of dicts with keys: id, name, type, stock_status,
            bed_occupancy_pct, attendance_pct, alert_count, health_score.
        """
        cutoff = date.today() - timedelta(days=30)
        results: list[dict[str, Any]] = []

        with get_db_session() as session:
            facilities = session.query(Facility).filter(Facility.is_active == True).all()  # noqa: E712

            for fac in facilities:
                # ── Stock health: % items at or above reorder level ──
                total_items = (
                    session.query(func.count(StockItem.id))
                    .filter(StockItem.facility_id == fac.id)
                    .scalar()
                    or 0
                )
                adequate_items = (
                    session.query(func.count(StockItem.id))
                    .filter(
                        StockItem.facility_id == fac.id,
                        StockItem.current_stock >= StockItem.reorder_level,
                    )
                    .scalar()
                    or 0
                )
                stock_health = (adequate_items / total_items * 100) if total_items > 0 else 100.0

                # ── Bed health: 100 - occupancy_pct ──
                bed_data = session.query(
                    func.sum(BedStatus.occupied_beds),
                    func.sum(BedStatus.total_beds),
                ).filter(BedStatus.facility_id == fac.id).first()
                occupied = bed_data[0] or 0
                total_beds = bed_data[1] or 1
                bed_occupancy_pct = round((occupied / total_beds) * 100, 1)
                bed_health = max(0.0, 100.0 - bed_occupancy_pct)

                # ── Attendance: present % in last 30 days ──
                total_att = (
                    session.query(func.count(DoctorAttendance.id))
                    .filter(
                        DoctorAttendance.facility_id == fac.id,
                        DoctorAttendance.date >= cutoff,
                    )
                    .scalar()
                    or 0
                )
                present_att = (
                    session.query(func.count(DoctorAttendance.id))
                    .filter(
                        DoctorAttendance.facility_id == fac.id,
                        DoctorAttendance.date >= cutoff,
                        DoctorAttendance.status == AttendanceStatus.PRESENT,
                    )
                    .scalar()
                    or 0
                )
                attendance_pct = (
                    round((present_att / total_att) * 100, 1) if total_att > 0 else 100.0
                )

                # ── Diagnostics: % available tests ──
                total_tests = (
                    session.query(func.count(TestAvailability.id))
                    .filter(TestAvailability.facility_id == fac.id)
                    .scalar()
                    or 0
                )
                available_tests = (
                    session.query(func.count(TestAvailability.id))
                    .filter(
                        TestAvailability.facility_id == fac.id,
                        TestAvailability.is_available == True,  # noqa: E712
                    )
                    .scalar()
                    or 0
                )
                diagnostics_health = (
                    (available_tests / total_tests * 100) if total_tests > 0 else 100.0
                )

                # ── Alert count ──
                alert_count = (
                    session.query(func.count(Alert.id))
                    .filter(
                        Alert.facility_id == fac.id,
                        Alert.is_resolved == False,  # noqa: E712
                    )
                    .scalar()
                    or 0
                )

                # ── Weighted health score ──
                health_score = round(
                    stock_health * 0.30
                    + attendance_pct * 0.25
                    + bed_health * 0.25
                    + diagnostics_health * 0.20,
                    1,
                )

                # Stock status label
                if stock_health >= 80:
                    stock_status = "Adequate"
                elif stock_health >= 50:
                    stock_status = "Low"
                else:
                    stock_status = "Critical"

                results.append(
                    {
                        "id": fac.id,
                        "name": fac.name,
                        "type": fac.facility_type.value if fac.facility_type else "",
                        "stock_status": stock_status,
                        "bed_occupancy_pct": bed_occupancy_pct,
                        "attendance_pct": attendance_pct,
                        "alert_count": alert_count,
                        "health_score": health_score,
                    }
                )

        # Sort by health score ascending (worst first)
        results.sort(key=lambda r: r["health_score"])
        return results

    # ── Latest Alerts ────────────────────────────────────────
    @staticmethod
    def get_latest_alerts(limit: int = 10) -> list[dict[str, Any]]:
        """
        Fetch the most recent unresolved alerts.

        Args:
            limit: Maximum number of alerts to return.

        Returns:
            List of alert dicts with facility_name joined.
        """
        with get_db_session() as session:
            rows = (
                session.query(Alert, Facility.name)
                .join(Facility, Alert.facility_id == Facility.id)
                .filter(Alert.is_resolved == False)  # noqa: E712
                .order_by(Alert.created_at.desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": alert.id,
                    "facility_name": fac_name,
                    "alert_type": alert.alert_type.value if alert.alert_type else "",
                    "severity": alert.severity.value if alert.severity else "",
                    "message": alert.message,
                    "created_at": alert.created_at.isoformat() if alert.created_at else "",
                }
                for alert, fac_name in rows
            ]

    # ── Resolve Alert ────────────────────────────────────────
    @staticmethod
    def resolve_alert(alert_id: int) -> bool:
        """
        Mark an alert as resolved.

        Args:
            alert_id: The ID of the alert to resolve.

        Returns:
            True if resolved successfully, False otherwise.
        """
        with get_db_session() as session:
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                alert.is_resolved = True
                alert.resolved_at = datetime.utcnow()
                return True
            return False

    # ── Quick Stats (sidebar) ────────────────────────────────
    @staticmethod
    def get_quick_stats() -> dict[str, int]:
        """Return quick counts for the sidebar."""
        with get_db_session() as session:
            return {
                "facilities": session.query(func.count(Facility.id)).scalar() or 0,
                "active_alerts": (
                    session.query(func.count(Alert.id))
                    .filter(Alert.is_resolved == False)  # noqa: E712
                    .scalar()
                    or 0
                ),
            }

    # ── Footfall Trend ───────────────────────────────────────
    @staticmethod
    def get_footfall_trend(days: int = 30) -> pd.DataFrame:
        """
        Daily total footfall across all facilities.

        Args:
            days: Number of historical days.

        Returns:
            DataFrame with columns ['date', 'total_footfall'].
        """
        cutoff = date.today() - timedelta(days=days)

        with get_db_session() as session:
            rows = (
                session.query(
                    Footfall.date,
                    func.sum(Footfall.patient_count).label("total_footfall"),
                )
                .filter(Footfall.date >= cutoff)
                .group_by(Footfall.date)
                .order_by(Footfall.date)
                .all()
            )

        if not rows:
            return pd.DataFrame(columns=["date", "total_footfall"])

        return pd.DataFrame(
            [{"date": r.date, "total_footfall": r.total_footfall} for r in rows]
        )

    # ── Stock Alert Summary ──────────────────────────────────
    @staticmethod
    def get_stock_alert_summary() -> pd.DataFrame:
        """
        Count of low-stock items per facility.

        Returns:
            DataFrame with columns ['facility_name', 'low_stock_count'].
        """
        with get_db_session() as session:
            rows = (
                session.query(
                    Facility.name.label("facility_name"),
                    func.count(StockItem.id).label("low_stock_count"),
                )
                .join(StockItem, StockItem.facility_id == Facility.id)
                .filter(StockItem.current_stock < StockItem.reorder_level)
                .group_by(Facility.name)
                .order_by(func.count(StockItem.id).desc())
                .all()
            )

        if not rows:
            return pd.DataFrame(columns=["facility_name", "low_stock_count"])

        return pd.DataFrame(
            [{"facility_name": r.facility_name, "low_stock_count": r.low_stock_count} for r in rows]
        )

    # ── Bed Occupancy Summary ────────────────────────────────
    @staticmethod
    def get_bed_occupancy_summary() -> pd.DataFrame:
        """
        Current bed occupancy percentage per facility.

        Returns:
            DataFrame with columns ['facility_name', 'occupancy_pct'].
        """
        with get_db_session() as session:
            rows = (
                session.query(
                    Facility.name.label("facility_name"),
                    func.sum(BedStatus.occupied_beds).label("occupied"),
                    func.sum(BedStatus.total_beds).label("total"),
                )
                .join(BedStatus, BedStatus.facility_id == Facility.id)
                .group_by(Facility.name)
                .all()
            )

        if not rows:
            return pd.DataFrame(columns=["facility_name", "occupancy_pct"])

        data = []
        for r in rows:
            total = r.total or 1
            pct = round((r.occupied or 0) / total * 100, 1)
            data.append({"facility_name": r.facility_name, "occupancy_pct": pct})

        return pd.DataFrame(data)
