"""
CareGrid AI — Attendance Service
====================================
Doctor attendance queries: facility-level summaries, monthly reports,
absenteeism trends, and calendar heatmap data.

Usage:
    from services.attendance_service import AttendanceService
    summary = AttendanceService.get_attendance_summary()
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Optional

import pandas as pd
from sqlalchemy import func, distinct

from models.database import get_db_session
from models.schema import DoctorAttendance, Facility
from config.constants import AttendanceStatus

logger = logging.getLogger(__name__)


class AttendanceService:
    """Static service for doctor-attendance analytics."""

    # ── Attendance by Facility ───────────────────────────────
    @staticmethod
    def get_attendance_by_facility(
        facility_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[dict[str, Any]]:
        """
        All attendance records for a facility, optionally date-filtered.

        Args:
            facility_id: Target facility.
            start_date: Inclusive start (optional).
            end_date: Inclusive end (optional).

        Returns:
            List of attendance dicts.
        """
        with get_db_session() as session:
            query = session.query(DoctorAttendance).filter(
                DoctorAttendance.facility_id == facility_id
            )
            if start_date is not None:
                query = query.filter(DoctorAttendance.date >= start_date)
            if end_date is not None:
                query = query.filter(DoctorAttendance.date <= end_date)

            rows = query.order_by(
                DoctorAttendance.date.desc(), DoctorAttendance.doctor_name
            ).all()

            return [
                {
                    "id": r.id,
                    "doctor_name": r.doctor_name,
                    "specialization": r.specialization,
                    "date": r.date.isoformat() if r.date else "",
                    "status": r.status.value if r.status else "",
                    "check_in": r.check_in,
                    "check_out": r.check_out,
                }
                for r in rows
            ]

    # ── Attendance Summary ───────────────────────────────────
    @staticmethod
    def get_attendance_summary() -> pd.DataFrame:
        """
        Per-facility attendance summary for the last 30 days.

        Returns:
            DataFrame with columns
            ['facility_name', 'total_doctors', 'present_pct', 'absent_pct'].
        """
        cutoff = date.today() - timedelta(days=30)

        with get_db_session() as session:
            facilities = session.query(Facility).filter(Facility.is_active == True).all()  # noqa: E712
            data: list[dict[str, Any]] = []

            for fac in facilities:
                total_records = (
                    session.query(func.count(DoctorAttendance.id))
                    .filter(
                        DoctorAttendance.facility_id == fac.id,
                        DoctorAttendance.date >= cutoff,
                    )
                    .scalar()
                    or 0
                )
                present_count = (
                    session.query(func.count(DoctorAttendance.id))
                    .filter(
                        DoctorAttendance.facility_id == fac.id,
                        DoctorAttendance.date >= cutoff,
                        DoctorAttendance.status == AttendanceStatus.PRESENT,
                    )
                    .scalar()
                    or 0
                )
                absent_count = (
                    session.query(func.count(DoctorAttendance.id))
                    .filter(
                        DoctorAttendance.facility_id == fac.id,
                        DoctorAttendance.date >= cutoff,
                        DoctorAttendance.status == AttendanceStatus.ABSENT,
                    )
                    .scalar()
                    or 0
                )
                total_doctors = (
                    session.query(
                        func.count(distinct(DoctorAttendance.doctor_name))
                    )
                    .filter(
                        DoctorAttendance.facility_id == fac.id,
                        DoctorAttendance.date >= cutoff,
                    )
                    .scalar()
                    or 0
                )

                present_pct = round((present_count / total_records) * 100, 1) if total_records > 0 else 0.0
                absent_pct = round((absent_count / total_records) * 100, 1) if total_records > 0 else 0.0

                data.append(
                    {
                        "facility_name": fac.name,
                        "total_doctors": total_doctors,
                        "present_pct": present_pct,
                        "absent_pct": absent_pct,
                    }
                )

        if not data:
            return pd.DataFrame(
                columns=["facility_name", "total_doctors", "present_pct", "absent_pct"]
            )

        return pd.DataFrame(data)

    # ── Monthly Summary ──────────────────────────────────────
    @staticmethod
    def get_monthly_summary(
        facility_id: int, year: int, month: int
    ) -> dict[str, Any]:
        """
        Attendance breakdown for a facility in a specific month.

        Args:
            facility_id: Target facility.
            year: Calendar year.
            month: Calendar month (1-12).

        Returns:
            Dict with total_days, present_count, absent_count,
            leave_count, percentage.
        """
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)

        with get_db_session() as session:
            base_q = session.query(func.count(DoctorAttendance.id)).filter(
                DoctorAttendance.facility_id == facility_id,
                DoctorAttendance.date >= start,
                DoctorAttendance.date <= end,
            )

            total_records = base_q.scalar() or 0
            present_count = (
                base_q.filter(
                    DoctorAttendance.status == AttendanceStatus.PRESENT
                ).scalar()
                or 0
            )

        # Re-query for absent and leave (session already used the base filter above,
        # so we open a fresh query for clarity)
        with get_db_session() as session:
            absent_count = (
                session.query(func.count(DoctorAttendance.id))
                .filter(
                    DoctorAttendance.facility_id == facility_id,
                    DoctorAttendance.date >= start,
                    DoctorAttendance.date <= end,
                    DoctorAttendance.status == AttendanceStatus.ABSENT,
                )
                .scalar()
                or 0
            )
            leave_count = (
                session.query(func.count(DoctorAttendance.id))
                .filter(
                    DoctorAttendance.facility_id == facility_id,
                    DoctorAttendance.date >= start,
                    DoctorAttendance.date <= end,
                    DoctorAttendance.status == AttendanceStatus.LEAVE,
                )
                .scalar()
                or 0
            )
            present_count = (
                session.query(func.count(DoctorAttendance.id))
                .filter(
                    DoctorAttendance.facility_id == facility_id,
                    DoctorAttendance.date >= start,
                    DoctorAttendance.date <= end,
                    DoctorAttendance.status == AttendanceStatus.PRESENT,
                )
                .scalar()
                or 0
            )

        total_days = (end - start).days + 1
        denominator = present_count + absent_count + leave_count
        percentage = round((present_count / denominator) * 100, 1) if denominator > 0 else 0.0

        return {
            "total_days": total_days,
            "present_count": present_count,
            "absent_count": absent_count,
            "leave_count": leave_count,
            "percentage": percentage,
        }

    # ── Doctor-Wise Summary ──────────────────────────────────
    @staticmethod
    def get_doctor_wise_summary(facility_id: int) -> pd.DataFrame:
        """
        Per-doctor attendance stats at a facility (all time).

        Args:
            facility_id: Target facility.

        Returns:
            DataFrame with columns
            ['doctor_name', 'specialization', 'present_days', 'absent_days', 'percentage'].
        """
        with get_db_session() as session:
            # Get all unique doctors at this facility
            doctors = (
                session.query(
                    DoctorAttendance.doctor_name,
                    DoctorAttendance.specialization,
                )
                .filter(DoctorAttendance.facility_id == facility_id)
                .distinct()
                .all()
            )

            data: list[dict[str, Any]] = []
            for doc_name, spec in doctors:
                present_days = (
                    session.query(func.count(DoctorAttendance.id))
                    .filter(
                        DoctorAttendance.facility_id == facility_id,
                        DoctorAttendance.doctor_name == doc_name,
                        DoctorAttendance.status == AttendanceStatus.PRESENT,
                    )
                    .scalar()
                    or 0
                )
                absent_days = (
                    session.query(func.count(DoctorAttendance.id))
                    .filter(
                        DoctorAttendance.facility_id == facility_id,
                        DoctorAttendance.doctor_name == doc_name,
                        DoctorAttendance.status == AttendanceStatus.ABSENT,
                    )
                    .scalar()
                    or 0
                )
                total = present_days + absent_days
                percentage = round((present_days / total) * 100, 1) if total > 0 else 0.0

                data.append(
                    {
                        "doctor_name": doc_name,
                        "specialization": spec,
                        "present_days": present_days,
                        "absent_days": absent_days,
                        "percentage": percentage,
                    }
                )

        if not data:
            return pd.DataFrame(
                columns=["doctor_name", "specialization", "present_days", "absent_days", "percentage"]
            )

        return pd.DataFrame(data).sort_values("percentage", ascending=True).reset_index(drop=True)

    # ── Absenteeism Trend ────────────────────────────────────
    @staticmethod
    def get_absenteeism_trend(
        facility_id: Optional[int] = None, days: int = 30
    ) -> pd.DataFrame:
        """
        Daily absenteeism rate over the last N days.

        Args:
            facility_id: Optional facility filter.
            days: Lookback window.

        Returns:
            DataFrame with columns ['date', 'absenteeism_rate'].
        """
        cutoff = date.today() - timedelta(days=days)

        with get_db_session() as session:
            # Total records per day
            total_q = session.query(
                DoctorAttendance.date,
                func.count(DoctorAttendance.id).label("total"),
            ).filter(DoctorAttendance.date >= cutoff)

            absent_q = session.query(
                DoctorAttendance.date,
                func.count(DoctorAttendance.id).label("absent"),
            ).filter(
                DoctorAttendance.date >= cutoff,
                DoctorAttendance.status == AttendanceStatus.ABSENT,
            )

            if facility_id is not None:
                total_q = total_q.filter(DoctorAttendance.facility_id == facility_id)
                absent_q = absent_q.filter(DoctorAttendance.facility_id == facility_id)

            total_rows = {
                r.date: r.total
                for r in total_q.group_by(DoctorAttendance.date).all()
            }
            absent_rows = {
                r.date: r.absent
                for r in absent_q.group_by(DoctorAttendance.date).all()
            }

        data: list[dict[str, Any]] = []
        for d, total in sorted(total_rows.items()):
            absent = absent_rows.get(d, 0)
            rate = round((absent / total) * 100, 1) if total > 0 else 0.0
            data.append({"date": d, "absenteeism_rate": rate})

        if not data:
            return pd.DataFrame(columns=["date", "absenteeism_rate"])

        return pd.DataFrame(data)

    # ── Attendance Calendar ──────────────────────────────────
    @staticmethod
    def get_attendance_calendar(
        facility_id: int, year: int, month: int
    ) -> list[dict[str, Any]]:
        """
        All attendance records for a calendar heatmap view.

        Args:
            facility_id: Target facility.
            year: Calendar year.
            month: Calendar month (1-12).

        Returns:
            List of dicts [{date, doctor_name, status}].
        """
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)

        with get_db_session() as session:
            rows = (
                session.query(DoctorAttendance)
                .filter(
                    DoctorAttendance.facility_id == facility_id,
                    DoctorAttendance.date >= start,
                    DoctorAttendance.date <= end,
                )
                .order_by(DoctorAttendance.date, DoctorAttendance.doctor_name)
                .all()
            )

            return [
                {
                    "date": r.date.isoformat() if r.date else "",
                    "doctor_name": r.doctor_name,
                    "status": r.status.value if r.status else "",
                }
                for r in rows
            ]
