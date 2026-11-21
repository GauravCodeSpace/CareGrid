"""
CareGrid AI — Reports Page
============================
Generate, preview, and export district and facility reports
in CSV and PDF formats.
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from utils.auth import require_auth
from utils.helper import section_header_html


def render_page() -> None:
    """Render the reports page."""
    if not require_auth():
        return

    st.markdown(
        '<div class="page-title">📄 Reports</div>'
        '<div class="page-subtitle">Generate, preview, and export healthcare reports</div>',
        unsafe_allow_html=True,
    )

    try:
        from services.report_service import ReportService
    except ImportError:
        st.error("Report service not available.")
        return

    # ── Report Configuration ──
    st.markdown(section_header_html("⚙️", "Report Configuration"), unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        report_type = st.selectbox(
            "Report Type",
            ["District Report", "Facility Report"],
            key="report_type_select",
        )

    facility_id = None
    with col2:
        if report_type == "Facility Report":
            from models.database import get_db_session
            from models.schema import Facility

            with get_db_session() as session:
                facilities = session.query(Facility).filter(
                    Facility.is_active == True  # noqa: E712
                ).all()
                facility_options = {f.name: f.id for f in facilities}

            selected_facility = st.selectbox(
                "Select Facility",
                options=list(facility_options.keys()),
                key="report_facility_select",
            )
            facility_id = facility_options.get(selected_facility)
        else:
            st.info("District-wide report covering all facilities.")

    with col3:
        date_range = st.date_input(
            "Date Range",
            value=(date.today() - timedelta(days=30), date.today()),
            key="report_date_range",
        )

    # Parse date range
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Generate Button ──
    generate_clicked = st.button(
        "📊 Generate Report", use_container_width=True,
        type="primary", key="generate_report_btn",
    )

    if generate_clicked:
        with st.spinner("Generating report..."):
            try:
                if report_type == "District Report":
                    report_df = ReportService.generate_district_report(start_date, end_date)
                    report_title = f"District Health Report ({start_date} to {end_date})"
                else:
                    report_df = ReportService.generate_facility_report(
                        facility_id, start_date, end_date
                    )
                    report_title = f"Facility Report — {selected_facility} ({start_date} to {end_date})"

                st.session_state["report_df"] = report_df
                st.session_state["report_title"] = report_title
                st.session_state["report_type_key"] = report_type.lower().replace(" ", "_")
            except Exception as e:
                st.error(f"Error generating report: {e}")

    # ── Display Report ──
    if "report_df" in st.session_state:
        report_df = st.session_state["report_df"]
        report_title = st.session_state.get("report_title", "Report")
        report_type_key = st.session_state.get("report_type_key", "district")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(section_header_html("📋", "Report Preview"), unsafe_allow_html=True)

        if report_df is not None and not report_df.empty:
            # Summary stats
            st.markdown(
                f"""<div class="glass-card">
                    <h3>📊 {report_title}</h3>
                    <p><strong>Records:</strong> {len(report_df)} |
                    <strong>Columns:</strong> {len(report_df.columns)} |
                    <strong>Generated:</strong> {date.today().strftime('%B %d, %Y')}</p>
                </div>""",
                unsafe_allow_html=True,
            )

            # Data table
            st.dataframe(
                report_df,
                use_container_width=True,
                hide_index=True,
                height=400,
            )

            # ── Export Buttons ──
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(section_header_html("📥", "Export Options"), unsafe_allow_html=True)

            exp_col1, exp_col2, exp_col3 = st.columns([1, 1, 2])

            with exp_col1:
                try:
                    csv_bytes = ReportService.export_csv(report_df)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_bytes,
                        file_name=f"caregrid_{report_type_key}_{date.today().isoformat()}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="download_csv_btn",
                    )
                except Exception as e:
                    st.error(f"CSV export error: {e}")

            with exp_col2:
                try:
                    pdf_bytes = ReportService.export_pdf(
                        report_df, report_type_key, report_title
                    )
                    st.download_button(
                        label="📥 Download PDF",
                        data=pdf_bytes,
                        file_name=f"caregrid_{report_type_key}_{date.today().isoformat()}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="download_pdf_btn",
                    )
                except Exception as e:
                    st.error(f"PDF export error: {e}")

            with exp_col3:
                st.caption(
                    "💡 Reports include all data for the selected date range. "
                    "PDF reports include summary statistics and CareGrid AI branding."
                )

            # ── Column Summary ──
            numeric_cols = report_df.select_dtypes(include=["number"]).columns.tolist()
            if numeric_cols:
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("📈 Statistical Summary"):
                    st.dataframe(
                        report_df[numeric_cols].describe().round(1),
                        use_container_width=True,
                    )
        else:
            st.warning("No data available for the selected criteria. Try adjusting the date range.")


# ── Page Entry Point ──
render_page()
