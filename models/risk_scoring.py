"""
CareGrid AI — Risk Scoring Model
==================================
Weighted composite risk scoring for healthcare facilities.
Calculates per-category scores and overall facility risk.

Risk Weights (from settings):
    Stock:       30%
    Attendance:  25%
    Beds:        25%
    Diagnostics: 20%

Usage:
    from models.risk_scoring import RiskScorer
    scorer = RiskScorer()
    risk = scorer.calculate_facility_risk(facility_id=1)
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func

from config.constants import AttendanceStatus
from config.settings import settings
from models.database import get_db_session
from models.schema import (
    Alert,
    BedStatus,
    DoctorAttendance,
    Facility,
    StockItem,
    TestAvailability,
)

logger = logging.getLogger(__name__)


class RiskScorer:
    """
    Calculates weighted risk scores for healthcare facilities.
    
    Score scale: 0 (no risk) to 100 (maximum risk).
    Risk levels:
        - healthy:  0-30
        - moderate: 31-50
        - warning:  51-75
        - critical: 76-100
    """

    @staticmethod
    def _calculate_stock_score(facility_id: int) -> tuple[float, list[str]]:
        """
        Calculate stock risk score based on percentage of items below reorder level.

        Args:
            facility_id: Facility ID.

        Returns:
            Tuple of (score 0-100, list of recommendations).
        """
        recommendations = []
        with get_db_session() as session:
            total_items = (
                session.query(func.count(StockItem.id))
                .filter(StockItem.facility_id == facility_id)
                .scalar()
            ) or 0

            if total_items == 0:
                return 0.0, ["No stock data available"]

            low_stock_items = (
                session.query(StockItem)
                .filter(
                    StockItem.facility_id == facility_id,
                    StockItem.current_stock < StockItem.reorder_level,
                )
                .all()
            )

            low_count = len(low_stock_items)
            score = (low_count / total_items) * 100

            # Critical items (stock < 25% of reorder level)
            critical_items = [
                item for item in low_stock_items
                if item.current_stock < item.reorder_level * 0.25
            ]

            if critical_items:
                recommendations.append(
                    f"URGENT: {len(critical_items)} medicine(s) critically low — "
                    f"immediate restocking required for: "
                    f"{', '.join(i.medicine_name for i in critical_items[:3])}"
                )
            elif low_count > 0:
                recommendations.append(
                    f"{low_count} medicine(s) below reorder level — "
                    f"schedule restocking within 48 hours"
                )

        return min(score, 100.0), recommendations

    @staticmethod
    def _calculate_attendance_score(facility_id: int) -> tuple[float, list[str]]:
        """
        Calculate attendance risk score based on recent absenteeism rate.

        Args:
            facility_id: Facility ID.

        Returns:
            Tuple of (score 0-100, list of recommendations).
        """
        recommendations = []
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        with get_db_session() as session:
            total_records = (
                session.query(func.count(DoctorAttendance.id))
                .filter(
                    DoctorAttendance.facility_id == facility_id,
                    DoctorAttendance.date >= start_date,
                    DoctorAttendance.date <= end_date,
                )
                .scalar()
            ) or 0

            if total_records == 0:
                return 0.0, ["No attendance data available"]

            absent_records = (
                session.query(func.count(DoctorAttendance.id))
                .filter(
                    DoctorAttendance.facility_id == facility_id,
                    DoctorAttendance.date >= start_date,
                    DoctorAttendance.date <= end_date,
                    DoctorAttendance.status == AttendanceStatus.ABSENT,
                )
                .scalar()
            ) or 0

            absenteeism_rate = absent_records / total_records
            score = absenteeism_rate * 100

            if absenteeism_rate > settings.HIGH_ABSENTEEISM_THRESHOLD:
                recommendations.append(
                    f"High absenteeism rate ({absenteeism_rate:.0%}) — "
                    f"review staffing and arrange backup doctors"
                )
            elif absenteeism_rate > 0.15:
                recommendations.append(
                    f"Moderate absenteeism ({absenteeism_rate:.0%}) — "
                    f"monitor attendance trends"
                )

        return min(score, 100.0), recommendations

    @staticmethod
    def _calculate_bed_score(facility_id: int) -> tuple[float, list[str]]:
        """
        Calculate bed occupancy risk score.

        Args:
            facility_id: Facility ID.

        Returns:
            Tuple of (score 0-100, list of recommendations).
        """
        recommendations = []

        with get_db_session() as session:
            # Get latest bed status records
            latest_date = (
                session.query(func.max(BedStatus.date))
                .filter(BedStatus.facility_id == facility_id)
                .scalar()
            )

            if latest_date is None:
                return 0.0, ["No bed occupancy data available"]

            bed_records = (
                session.query(BedStatus)
                .filter(
                    BedStatus.facility_id == facility_id,
                    BedStatus.date == latest_date,
                )
                .all()
            )

            if not bed_records:
                return 0.0, ["No bed records found"]

            total_beds = sum(b.total_beds for b in bed_records)
            occupied_beds = sum(b.occupied_beds for b in bed_records)

            if total_beds == 0:
                return 0.0, ["No beds configured"]

            occupancy_rate = occupied_beds / total_beds
            score = occupancy_rate * 100

            # Check for critically full wards
            critical_wards = [
                b for b in bed_records
                if b.total_beds > 0 and (b.occupied_beds / b.total_beds) > 0.90
            ]

            if occupancy_rate > settings.CRITICAL_BED_OCCUPANCY_THRESHOLD:
                recommendations.append(
                    f"CRITICAL: Bed occupancy at {occupancy_rate:.0%} — "
                    f"activate overflow protocols and divert patients"
                )
            elif occupancy_rate > settings.HIGH_BED_OCCUPANCY_THRESHOLD:
                recommendations.append(
                    f"High bed occupancy ({occupancy_rate:.0%}) — "
                    f"prepare contingency beds"
                )

            if critical_wards:
                ward_names = [b.ward_type.value for b in critical_wards]
                recommendations.append(
                    f"Wards near capacity: {', '.join(ward_names)}"
                )

        return min(score, 100.0), recommendations

    @staticmethod
    def _calculate_diagnostic_score(facility_id: int) -> tuple[float, list[str]]:
        """
        Calculate diagnostic availability risk score.

        Args:
            facility_id: Facility ID.

        Returns:
            Tuple of (score 0-100, list of recommendations).
        """
        recommendations = []

        with get_db_session() as session:
            total_tests = (
                session.query(func.count(TestAvailability.id))
                .filter(TestAvailability.facility_id == facility_id)
                .scalar()
            ) or 0

            if total_tests == 0:
                return 0.0, ["No diagnostic test data available"]

            unavailable_tests = (
                session.query(TestAvailability)
                .filter(
                    TestAvailability.facility_id == facility_id,
                    TestAvailability.is_available == False,  # noqa: E712
                )
                .all()
            )

            unavailable_count = len(unavailable_tests)
            score = (unavailable_count / total_tests) * 100

            if unavailable_count > 0:
                test_names = [t.test_name for t in unavailable_tests[:3]]
                out_of_order = [
                    t for t in unavailable_tests
                    if t.equipment_status == "out_of_order"
                ]
                recommendations.append(
                    f"{unavailable_count} diagnostic test(s) unavailable: "
                    f"{', '.join(test_names)}"
                )
                if out_of_order:
                    recommendations.append(
                        f"{len(out_of_order)} equipment(s) out of order — "
                        f"schedule maintenance"
                    )

        return min(score, 100.0), recommendations

    def calculate_facility_risk(self, facility_id: int) -> dict:
        """
        Calculate comprehensive risk score for a facility.

        Args:
            facility_id: Facility ID.

        Returns:
            Dictionary with risk breakdown:
                - facility_id, facility_name
                - stock_score, attendance_score, bed_score, diagnostic_score
                - overall_score, risk_level
                - recommendations (list of strings)
        """
        # Get facility name
        with get_db_session() as session:
            facility = session.query(Facility).filter_by(id=facility_id).first()
            if not facility:
                return {"error": f"Facility {facility_id} not found"}
            facility_name = facility.name

        # Calculate individual scores
        stock_score, stock_recs = self._calculate_stock_score(facility_id)
        attendance_score, attendance_recs = self._calculate_attendance_score(facility_id)
        bed_score, bed_recs = self._calculate_bed_score(facility_id)
        diagnostic_score, diagnostic_recs = self._calculate_diagnostic_score(facility_id)

        # Weighted overall score
        overall_score = (
            stock_score * settings.RISK_WEIGHT_STOCK
            + attendance_score * settings.RISK_WEIGHT_ATTENDANCE
            + bed_score * settings.RISK_WEIGHT_BEDS
            + diagnostic_score * settings.RISK_WEIGHT_DIAGNOSTICS
        )

        # Determine risk level
        if overall_score > 75:
            risk_level = "critical"
        elif overall_score > 50:
            risk_level = "warning"
        elif overall_score > 30:
            risk_level = "moderate"
        else:
            risk_level = "healthy"

        # Consolidate recommendations
        all_recommendations = stock_recs + attendance_recs + bed_recs + diagnostic_recs

        return {
            "facility_id": facility_id,
            "facility_name": facility_name,
            "stock_score": round(stock_score, 1),
            "attendance_score": round(attendance_score, 1),
            "bed_score": round(bed_score, 1),
            "diagnostic_score": round(diagnostic_score, 1),
            "overall_score": round(overall_score, 1),
            "risk_level": risk_level,
            "recommendations": all_recommendations,
        }

    def calculate_all_risks(self) -> list[dict]:
        """
        Calculate risk scores for all active facilities.

        Returns:
            List of risk score dictionaries sorted by overall_score descending.
        """
        with get_db_session() as session:
            facilities = (
                session.query(Facility)
                .filter(Facility.is_active == True)  # noqa: E712
                .all()
            )
            facility_ids = [f.id for f in facilities]

        results = []
        for fid in facility_ids:
            try:
                risk = self.calculate_facility_risk(fid)
                if "error" not in risk:
                    results.append(risk)
            except Exception as e:
                logger.error("Error calculating risk for facility %d: %s", fid, e)

        # Sort by overall score descending (highest risk first)
        results.sort(key=lambda x: x["overall_score"], reverse=True)
        return results
