"""
CareGrid AI — Report Service
==============================
Generates district and facility reports with CSV and PDF export.

Usage:
    from services.report_service import ReportService
    df = ReportService.generate_district_report(start_date, end_date)
    csv_bytes = ReportService.export_csv(df, "report.csv")
    pdf_bytes = ReportService.export_pdf(df, "district", "District Report")
"""

from __future__ import annotations

import io
import logging
from datetime import date, datetime
from typing import Optional

import pandas as pd
from fpdf import FPDF
from sqlalchemy import func

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
from config.constants import AttendanceStatus

logger = logging.getLogger(__name__)


class ReportService:
    """Service for generating and exporting healthcare reports."""

    @staticmethod
    def generate_district_report(
        start_date: date, end_date: date
    ) -> pd.DataFrame:
        """
        Generate a comprehensive district-level report.

        Args:
            start_date: Report start date.
            end_date: Report end date.

        Returns:
            DataFrame with per-facility summary data.
        """
        with get_db_session() as session:
            facilities = (
                session.query(Facility)
                .filter(Facility.is_active == True)  # noqa: E712
                .all()
            )

            rows = []
            for facility in facilities:
                # Stock summary
                total_items = (
                    session.query(func.count(StockItem.id))
                    .filter(StockItem.facility_id == facility.id)
                    .scalar()
                ) or 0

                low_stock = (
                    session.query(func.count(StockItem.id))
                    .filter(
                        StockItem.facility_id == facility.id,
                        StockItem.current_stock < StockItem.reorder_level,
                    )
                    .scalar()
                ) or 0

                # Footfall summary
                total_footfall = (
                    session.query(func.sum(Footfall.patient_count))
                    .filter(
                        Footfall.facility_id == facility.id,
                        Footfall.date >= start_date,
                        Footfall.date <= end_date,
                    )
                    .scalar()
                ) or 0

                # Bed occupancy (latest)
                latest_beds = (
                    session.query(
                        func.sum(BedStatus.total_beds),
                        func.sum(BedStatus.occupied_beds),
                    )
                    .filter(BedStatus.facility_id == facility.id)
                    .filter(
                        BedStatus.date == session.query(func.max(BedStatus.date))
                        .filter(BedStatus.facility_id == facility.id)
                        .scalar()
                    )
                    .first()
                )
                total_beds = latest_beds[0] or 0
                occupied_beds = latest_beds[1] or 0
                occupancy_pct = (
                    round((occupied_beds / total_beds) * 100, 1)
                    if total_beds > 0 else 0
                )

                # Attendance
                total_attendance = (
                    session.query(func.count(DoctorAttendance.id))
                    .filter(
                        DoctorAttendance.facility_id == facility.id,
                        DoctorAttendance.date >= start_date,
                        DoctorAttendance.date <= end_date,
                    )
                    .scalar()
                ) or 0

                present_count = (
                    session.query(func.count(DoctorAttendance.id))
                    .filter(
                        DoctorAttendance.facility_id == facility.id,
                        DoctorAttendance.date >= start_date,
                        DoctorAttendance.date <= end_date,
                        DoctorAttendance.status == AttendanceStatus.PRESENT,
                    )
                    .scalar()
                ) or 0

                attendance_pct = (
                    round((present_count / total_attendance) * 100, 1)
                    if total_attendance > 0 else 0
                )

                # Active alerts
                alert_count = (
                    session.query(func.count(Alert.id))
                    .filter(
                        Alert.facility_id == facility.id,
                        Alert.is_resolved == False,  # noqa: E712
                    )
                    .scalar()
                ) or 0

                rows.append({
                    "Facility": facility.name,
                    "Type": facility.facility_type.value,
                    "Total Stock Items": total_items,
                    "Low Stock Items": low_stock,
                    "Total Footfall": total_footfall,
                    "Total Beds": total_beds,
                    "Occupied Beds": occupied_beds,
                    "Bed Occupancy %": occupancy_pct,
                    "Attendance %": attendance_pct,
                    "Active Alerts": alert_count,
                })

            return pd.DataFrame(rows)

    @staticmethod
    def generate_facility_report(
        facility_id: int, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """
        Generate a detailed report for a specific facility.

        Args:
            facility_id: Facility ID.
            start_date: Report start date.
            end_date: Report end date.

        Returns:
            DataFrame with detailed facility metrics.
        """
        with get_db_session() as session:
            facility = session.query(Facility).filter_by(id=facility_id).first()
            if not facility:
                return pd.DataFrame()

            # Stock details
            stock_items = (
                session.query(StockItem)
                .filter(StockItem.facility_id == facility_id)
                .all()
            )

            rows = []
            for item in stock_items:
                status = "Adequate"
                if item.current_stock < item.reorder_level * 0.25:
                    status = "Critical"
                elif item.current_stock < item.reorder_level:
                    status = "Low"

                rows.append({
                    "Facility": facility.name,
                    "Category": "Stock",
                    "Metric": item.medicine_name,
                    "Value": item.current_stock,
                    "Unit": item.unit,
                    "Status": status,
                    "Threshold": item.reorder_level,
                })

            # Footfall by department
            footfall_data = (
                session.query(
                    Footfall.department,
                    func.sum(Footfall.patient_count).label("total"),
                )
                .filter(
                    Footfall.facility_id == facility_id,
                    Footfall.date >= start_date,
                    Footfall.date <= end_date,
                )
                .group_by(Footfall.department)
                .all()
            )

            for dept, total in footfall_data:
                rows.append({
                    "Facility": facility.name,
                    "Category": "Footfall",
                    "Metric": dept,
                    "Value": total or 0,
                    "Unit": "patients",
                    "Status": "—",
                    "Threshold": "—",
                })

            # Bed status
            bed_records = (
                session.query(BedStatus)
                .filter(
                    BedStatus.facility_id == facility_id,
                    BedStatus.date == session.query(func.max(BedStatus.date))
                    .filter(BedStatus.facility_id == facility_id)
                    .scalar(),
                )
                .all()
            )

            for bed in bed_records:
                occ_pct = (
                    round((bed.occupied_beds / bed.total_beds) * 100, 1)
                    if bed.total_beds > 0 else 0
                )
                status = "Normal"
                if occ_pct > 95:
                    status = "Critical"
                elif occ_pct > 85:
                    status = "High"

                rows.append({
                    "Facility": facility.name,
                    "Category": "Beds",
                    "Metric": f"{bed.ward_type.value} Ward",
                    "Value": f"{bed.occupied_beds}/{bed.total_beds}",
                    "Unit": f"{occ_pct}% occupied",
                    "Status": status,
                    "Threshold": "85%",
                })

            return pd.DataFrame(rows) if rows else pd.DataFrame()

    @staticmethod
    def export_csv(df: pd.DataFrame, filename: str = "report.csv") -> bytes:
        """
        Export DataFrame as CSV bytes.

        Args:
            df: DataFrame to export.
            filename: Filename hint.

        Returns:
            CSV content as bytes.
        """
        buffer = io.StringIO()
        df.to_csv(buffer, index=False, encoding="utf-8")
        return buffer.getvalue().encode("utf-8")

    @staticmethod
    def _clean_txt(text: Any) -> str:
        """Sanitize text to be compatible with Helvetica/Latin-1 encoding."""
        if text is None:
            return ""
        s = str(text)
        # Replace em-dashes and en-dashes with standard hyphens
        s = s.replace("—", "-").replace("–", "-")
        # Replace smart quotes with standard quotes
        s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
        # Encode to latin-1 and replace any unsupported characters with '?'
        return s.encode("latin-1", "replace").decode("latin-1")

    @staticmethod
    def export_pdf(
        df: pd.DataFrame,
        report_type: str = "district",
        title: str = "CareGrid AI Report",
    ) -> bytes:
        """
        Export DataFrame as a professionally formatted PDF.

        Args:
            df: DataFrame with report data.
            report_type: 'district' or 'facility'.
            title: Report title.

        Returns:
            PDF content as bytes.
        """

        class HealthcarePDF(FPDF):
            """Custom PDF with healthcare branding."""

            def header(self):
                # Blue header bar
                self.set_fill_color(37, 99, 235)
                self.rect(0, 0, 210, 25, "F")
                self.set_font("Helvetica", "B", 16)
                self.set_text_color(255, 255, 255)
                self.set_y(6)
                self.cell(0, 12, "CareGrid AI", align="L")
                self.set_font("Helvetica", "", 9)
                self.cell(0, 12, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="R")
                self.ln(18)

            def footer(self):
                self.set_y(-15)
                self.set_font("Helvetica", "I", 8)
                self.set_text_color(100, 100, 100)
                self.cell(
                    0, 10,
                    f"Page {self.page_no()}/{{nb}} | CONFIDENTIAL - District Health Administration",
                    align="C",
                )

        pdf = HealthcarePDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=20)

        # Report title
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(30, 41, 59)
        pdf.ln(5)
        pdf.cell(0, 10, ReportService._clean_txt(title), ln=True)

        # Subtitle
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(100, 116, 139)
        subtitle_text = f"Report Type: {report_type.title()} | Records: {len(df)}"
        pdf.cell(0, 6, ReportService._clean_txt(subtitle_text), ln=True)
        pdf.ln(5)

        # Separator line
        pdf.set_draw_color(37, 99, 235)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        if df.empty:
            pdf.set_font("Helvetica", "", 12)
            pdf.cell(0, 10, "No data available for the selected criteria.", ln=True)
        else:
            # Table header
            columns = list(df.columns)
            col_width = min(180 / len(columns), 40)

            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(37, 99, 235)
            pdf.set_text_color(255, 255, 255)

            for col in columns:
                clean_col = ReportService._clean_txt(str(col)[:15])
                pdf.cell(col_width, 8, clean_col, border=1, fill=True, align="C")
            pdf.ln()

            # Table rows
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(30, 41, 59)

            for idx, row in df.iterrows():
                if idx % 2 == 0:
                    pdf.set_fill_color(248, 250, 252)
                else:
                    pdf.set_fill_color(255, 255, 255)

                for col in columns:
                    value = ReportService._clean_txt(str(row[col])[:18])
                    pdf.cell(col_width, 7, value, border=1, fill=True, align="C")
                pdf.ln()

            # Summary section
            pdf.ln(10)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(0, 8, "Summary Statistics", ln=True)
            pdf.set_draw_color(37, 99, 235)
            pdf.line(10, pdf.get_y(), 100, pdf.get_y())
            pdf.ln(3)

            pdf.set_font("Helvetica", "", 9)
            summary_recs = f"Total Records: {len(df)}"
            pdf.cell(0, 6, ReportService._clean_txt(summary_recs), ln=True)

            # Add numeric column summaries
            numeric_cols = df.select_dtypes(include=["number"]).columns
            for col in numeric_cols[:5]:
                stat_text = (
                    f"{col}: Mean={df[col].mean():.1f}, "
                    f"Min={df[col].min()}, Max={df[col].max()}"
                )
                pdf.cell(
                    0, 6,
                    ReportService._clean_txt(stat_text),
                    ln=True,
                )

        return bytes(pdf.output())
