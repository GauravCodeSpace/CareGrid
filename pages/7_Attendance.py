"""
CareGrid AI — Doctor Attendance Page
======================================
Displays attendance calendar, monthly percentages,
absenteeism trends, and doctor-wise breakdown.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta

from utils.auth import require_auth
from utils.helper import format_number, format_percentage, section_header_html, status_badge_html


def render_page() -> None:
    """Render the doctor attendance monitoring page."""
    if not require_auth():
        return

    st.markdown(
        '<div class="page-title">📋 Doctor Attendance</div>'
        '<div class="page-subtitle">Monitor attendance, absenteeism trends, and staffing levels</div>',
        unsafe_allow_html=True,
    )

    try:
        from services.attendance_service import AttendanceService
    except ImportError:
        st.error("Attendance service not available. Please ensure the application is set up correctly.")
        return

    # ── Filters ──
    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])

    user_role = st.session_state.get("user_role", "")
    user_facility_id = st.session_state.get("user_facility_id")

    with col_f1:
        from models.database import get_db_session
        from models.schema import Facility
        with get_db_session() as session:
            if user_role == "Facility Staff" and user_facility_id is not None:
                facilities = session.query(Facility).filter(Facility.id == user_facility_id).all()
            else:
                facilities = session.query(Facility).filter(Facility.is_active == True).all()
            facility_options = {f.name: f.id for f in facilities}

        if len(facility_options) == 1:
            selected_facility = list(facility_options.keys())[0]
            st.text_input("Facility", value=selected_facility, disabled=True)
            facility_id = facility_options[selected_facility]
        else:
            selected_facility = st.selectbox(
                "Select Facility",
                options=list(facility_options.keys()),
                key="attendance_facility_select",
            )
            facility_id = facility_options.get(selected_facility)

    with col_f2:
        current_year = date.today().year
        selected_year = st.selectbox(
            "Year", options=list(range(current_year, current_year - 3, -1)),
            key="attendance_year_select",
        )

    with col_f3:
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        current_month = date.today().month
        selected_month = st.selectbox(
            "Month", options=month_names, index=current_month - 1,
            key="attendance_month_select",
        )
        month_num = month_names.index(selected_month) + 1

    st.markdown("<br>", unsafe_allow_html=True)

    # ── KPIs ──
    try:
        summary = AttendanceService.get_monthly_summary(facility_id, selected_year, month_num)
    except Exception:
        summary = {"total_days": 0, "present_count": 0, "absent_count": 0, "leave_count": 0, "percentage": 0}

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Total Records", format_number(summary.get("total_days", 0)))
    with kpi2:
        st.metric("Present Days", format_number(summary.get("present_count", 0)), delta="✅")
    with kpi3:
        st.metric("Absent Days", format_number(summary.get("absent_count", 0)), delta="⚠️", delta_color="inverse")
    with kpi4:
        pct = summary.get("percentage", 0)
        color_hint = "normal" if pct >= 80 else "inverse"
        st.metric("Attendance %", f"{pct:.1f}%", delta_color=color_hint)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Attendance Marker Form ──
    with st.expander("✍️ Mark/Update Daily Doctor Attendance"):
        with st.form("mark_attendance_form", clear_on_submit=True):
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                # Fetch registered doctors for this facility to show in dropdown
                from models.database import get_db_session
                from models.schema import DoctorAttendance as DocAttModel
                
                with get_db_session() as session:
                    existing_docs = (
                        session.query(DocAttModel.doctor_name, DocAttModel.specialization)
                        .filter(DocAttModel.facility_id == facility_id)
                        .distinct(DocAttModel.doctor_name)
                        .all()
                    )
                    doc_options = {d[0]: d[1] for d in existing_docs}
                
                if doc_options:
                    selected_doc = st.selectbox(
                        "Select Doctor to Mark",
                        options=list(doc_options.keys()),
                        key="mark_doc_select"
                    )
                    doc_spec = doc_options[selected_doc]
                else:
                    st.warning("No doctors registered at this facility. Add them in the Admin Panel.")
                    selected_doc = None
                    doc_spec = ""
                    
            with col_m2:
                att_status = st.selectbox(
                    "Attendance Status",
                    ["Present", "Absent", "On Leave", "Half Day"],
                    key="mark_status_select"
                )
                att_date = st.date_input("Date", value=date.today())
                
            submitted = st.form_submit_button("📋 Submit Attendance")
            
            if submitted and selected_doc:
                status_mapping = {
                    "Present": "present",
                    "Absent": "absent",
                    "On Leave": "leave",
                    "Half Day": "half_day"
                }
                db_status = status_mapping[att_status]
                
                try:
                    from models.database import get_db_session
                    from models.schema import DoctorAttendance as DocAttModel
                    from config.constants import AttendanceStatus
                    
                    with get_db_session() as session:
                        # check if attendance already marked for this date
                        existing = session.query(DocAttModel).filter(
                            DocAttModel.facility_id == facility_id,
                            DocAttModel.doctor_name == selected_doc,
                            DocAttModel.date == att_date
                        ).first()
                        
                        if existing:
                            existing.status = AttendanceStatus(db_status)
                            st.success(f"Updated attendance for {selected_doc} on {att_date} as {att_status}!")
                        else:
                            new_rec = DocAttModel(
                                facility_id=facility_id,
                                doctor_name=selected_doc,
                                specialization=doc_spec,
                                date=att_date,
                                status=AttendanceStatus(db_status)
                            )
                            session.add(new_rec)
                            st.success(f"Logged attendance for {selected_doc} on {att_date} as {att_status}!")
                        session.commit()
                        st.rerun()
                except Exception as e:
                    st.error(f"Error marking attendance: {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ──
    tab_trend, tab_calendar, tab_doctors = st.tabs(["📈 Trend Analysis", "📅 Attendance Calendar", "👨‍⚕️ Doctor-wise"])

    # ── Trend Tab ──
    with tab_trend:
        st.markdown(section_header_html("📊", "Absenteeism Trend (Last 30 Days)"), unsafe_allow_html=True)

        try:
            trend_df = AttendanceService.get_absenteeism_trend(facility_id, days=30)
            if trend_df is not None and not trend_df.empty:
                from utils.charts import create_area_chart
                fig = create_area_chart(
                    trend_df, x="date", y="absenteeism_rate",
                    title="Daily Absenteeism Rate (%)",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No trend data available for this facility.")
        except Exception as e:
            st.warning(f"Unable to load trend data: {e}")

        # Monthly gauge
        st.markdown(section_header_html("📊", "Monthly Attendance Rate"), unsafe_allow_html=True)
        try:
            from utils.charts import create_gauge_chart
            gauge_fig = create_gauge_chart(
                value=summary.get("percentage", 0),
                max_val=100,
                title=f"Attendance % — {selected_month} {selected_year}",
                ranges=[
                    (0, 60, "#FEE2E2"),
                    (60, 80, "#FEF3C7"),
                    (80, 100, "#DCFCE7"),
                ],
            )
            st.plotly_chart(gauge_fig, use_container_width=True)
        except Exception:
            st.info(f"Attendance rate: {summary.get('percentage', 0):.1f}%")

    # ── Calendar Tab ──
    with tab_calendar:
        st.markdown(section_header_html("📅", "Attendance Heatmap"), unsafe_allow_html=True)

        try:
            calendar_data = AttendanceService.get_attendance_calendar(facility_id, selected_year, month_num)
            if calendar_data:
                # Build heatmap: doctors (y) vs days (x)
                df_cal = pd.DataFrame(calendar_data)
                doctors = df_cal["doctor_name"].unique().tolist()
                
                import calendar
                _, days_in_month = calendar.monthrange(selected_year, month_num)
                day_labels = [str(d) for d in range(1, days_in_month + 1)]

                status_map = {"present": 1, "absent": 0, "leave": 0.5, "half_day": 0.5}
                matrix = []
                for doc in doctors:
                    doc_data = df_cal[df_cal["doctor_name"] == doc]
                    row = []
                    for d in range(1, days_in_month + 1):
                        day_record = doc_data[pd.to_datetime(doc_data["date"]).dt.day == d]
                        if not day_record.empty:
                            status = day_record.iloc[0]["status"]
                            row.append(status_map.get(status, 0))
                        else:
                            row.append(float("nan"))
                    matrix.append(row)

                from utils.charts import create_heatmap
                fig = create_heatmap(
                    np.array(matrix), day_labels, doctors,
                    f"Attendance — {selected_month} {selected_year}",
                    colorscale=[[0, "#EF4444"], [0.5, "#F59E0B"], [1, "#22C55E"]],
                )
                st.plotly_chart(fig, use_container_width=True)

                st.markdown(
                    """<div style="display:flex;gap:16px;margin-top:8px;">
                    <span style="display:inline-flex;align-items:center;gap:4px;">
                        <span style="width:16px;height:16px;background:#22C55E;border-radius:3px;display:inline-block;"></span> Present
                    </span>
                    <span style="display:inline-flex;align-items:center;gap:4px;">
                        <span style="width:16px;height:16px;background:#F59E0B;border-radius:3px;display:inline-block;"></span> Leave / Half Day
                    </span>
                    <span style="display:inline-flex;align-items:center;gap:4px;">
                        <span style="width:16px;height:16px;background:#EF4444;border-radius:3px;display:inline-block;"></span> Absent
                    </span>
                    </div>""",
                    unsafe_allow_html=True,
                )
            else:
                st.info("No calendar data available for this period.")
        except Exception as e:
            st.warning(f"Unable to load calendar data: {e}")

    # ── Doctor-wise Tab ──
    with tab_doctors:
        st.markdown(section_header_html("👨‍⚕️", "Doctor-wise Attendance Summary"), unsafe_allow_html=True)

        try:
            doc_df = AttendanceService.get_doctor_wise_summary(facility_id)
            if doc_df is not None and not doc_df.empty:
                # Add status column
                def _get_status(pct):
                    if pct >= 90:
                        return "Excellent"
                    elif pct >= 75:
                        return "Good"
                    elif pct >= 60:
                        return "Needs Attention"
                    else:
                        return "Critical"

                doc_df["Status"] = doc_df["percentage"].apply(_get_status)

                st.dataframe(
                    doc_df.style.background_gradient(subset=["percentage"], cmap="RdYlGn", vmin=0, vmax=100),
                    use_container_width=True,
                    hide_index=True,
                )

                # Bar chart
                from utils.charts import create_bar_chart
                fig = create_bar_chart(
                    doc_df, x="doctor_name", y="percentage",
                    title="Attendance Rate by Doctor",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No doctor-wise data available.")
        except Exception as e:
            st.warning(f"Unable to load doctor data: {e}")


# ── Page Entry Point ──
render_page()
