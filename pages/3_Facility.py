"""
CareGrid AI — Facility Details Page
======================================
Detailed view of individual healthcare facilities with
stock, beds, attendance, and diagnostics tabs.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
import random

# ── Service imports ──
try:
    from services.dashboard_service import DashboardService
    _DASHBOARD_SVC = True
except ImportError:
    _DASHBOARD_SVC = False

try:
    from services.stock_service import StockService
    _STOCK_SVC = True
except ImportError:
    _STOCK_SVC = False

try:
    from services.attendance_service import AttendanceService
    _ATTENDANCE_SVC = True
except ImportError:
    _ATTENDANCE_SVC = False

try:
    from utils.translator import t
except ImportError:
    def t(key: str, **kwargs) -> str:
        return key

from config.constants import (
    Colors, ICONS, MEDICINES, DEPARTMENTS, DIAGNOSTIC_TESTS,
    WardType, AttendanceStatus,
)


# ── Auth guard ──
if not st.session_state.get("authenticated"):
    st.switch_page("pages/1_Login.py")


# ── Demo Data ──
DEMO_FACILITIES = [
    {"id": 1, "name": "PHC Rajpur", "type": "PHC", "address": "Rajpur Road, Block A, Lucknow 226001",
     "phone": "+91 522-2740001", "capacity": 30, "lat": 26.88, "lon": 80.91},
    {"id": 2, "name": "CHC Sadar", "type": "CHC", "address": "Sadar Bazaar, Main Road, Lucknow 226003",
     "phone": "+91 522-2740002", "capacity": 80, "lat": 26.85, "lon": 80.95},
    {"id": 3, "name": "PHC Mohanlalganj", "type": "PHC", "address": "NH-56, Mohanlalganj, Lucknow 226301",
     "phone": "+91 522-2740003", "capacity": 25, "lat": 26.75, "lon": 80.88},
    {"id": 4, "name": "CHC Malihabad", "type": "CHC", "address": "Malihabad Road, Lucknow 226102",
     "phone": "+91 522-2740004", "capacity": 60, "lat": 26.92, "lon": 80.72},
    {"id": 5, "name": "PHC Bakshi Ka Talab", "type": "PHC", "address": "BKT Main Road, Lucknow 226021",
     "phone": "+91 522-2740005", "capacity": 35, "lat": 26.91, "lon": 80.94},
    {"id": 6, "name": "PHC Chinhat", "type": "PHC", "address": "Chinhat-Deva Road, Lucknow 226028",
     "phone": "+91 522-2740006", "capacity": 30, "lat": 26.89, "lon": 81.03},
    {"id": 7, "name": "CHC Kakori", "type": "CHC", "address": "Kakori Town, Lucknow 226101",
     "phone": "+91 522-2740007", "capacity": 70, "lat": 26.87, "lon": 80.79},
    {"id": 8, "name": "PHC Gosainganj", "type": "PHC", "address": "Gosainganj, Lucknow 226302",
     "phone": "+91 522-2740008", "capacity": 25, "lat": 26.78, "lon": 80.81},
    {"id": 9, "name": "PHC Itaunja", "type": "PHC", "address": "Itaunja Block, Lucknow 226201",
     "phone": "+91 522-2740009", "capacity": 30, "lat": 27.02, "lon": 80.90},
    {"id": 10, "name": "CHC Nagram", "type": "CHC", "address": "Nagram Road, Lucknow 226303",
     "phone": "+91 522-2740010", "capacity": 55, "lat": 26.72, "lon": 80.85},
    {"id": 11, "name": "PHC Mal", "type": "PHC", "address": "Mal Block, Lucknow 226029",
     "phone": "+91 522-2740011", "capacity": 20, "lat": 26.84, "lon": 81.08},
    {"id": 12, "name": "PHC Sarojininagar", "type": "PHC", "address": "Sarojini Nagar, Lucknow 226008",
     "phone": "+91 522-2740012", "capacity": 35, "lat": 26.79, "lon": 80.92},
    {"id": 13, "name": "CHC Mohanlalganj Block", "type": "CHC", "address": "Block HQ, Mohanlalganj 226301",
     "phone": "+91 522-2740013", "capacity": 65, "lat": 26.76, "lon": 80.83},
    {"id": 14, "name": "PHC Amaniganj", "type": "PHC", "address": "Amaniganj, Lucknow 226004",
     "phone": "+91 522-2740014", "capacity": 25, "lat": 26.83, "lon": 80.97},
    {"id": 15, "name": "PHC Nilmatha", "type": "PHC", "address": "Nilmatha, Lucknow 226002",
     "phone": "+91 522-2740015", "capacity": 30, "lat": 26.90, "lon": 80.86},
]


def _demo_stock_items(facility_name: str) -> pd.DataFrame:
    rows = []
    for med in MEDICINES:
        stock = random.randint(10, med["reorder_level"] * 3)
        status = "Adequate" if stock > med["reorder_level"] else ("Low" if stock > med["reorder_level"] * 0.3 else "Critical")
        rows.append({
            "Medicine": med["name"], "Category": med["category"],
            "Current Stock": stock, "Reorder Level": med["reorder_level"],
            "Unit": med["unit"], "Status": status,
        })
    return pd.DataFrame(rows)


def _demo_bed_status() -> list[dict]:
    wards = [
        {"ward": "General", "total": 20, "icon": "🛏️"},
        {"ward": "ICU", "total": 5, "icon": "🫀"},
        {"ward": "Maternity", "total": 8, "icon": "👶"},
        {"ward": "Pediatric", "total": 6, "icon": "🧒"},
        {"ward": "Emergency", "total": 4, "icon": "🚑"},
    ]
    for w in wards:
        w["occupied"] = random.randint(0, w["total"])
        w["available"] = w["total"] - w["occupied"]
        w["occupancy_pct"] = round(w["occupied"] / w["total"] * 100, 1) if w["total"] > 0 else 0
    return wards


def _demo_attendance() -> pd.DataFrame:
    doctors = [
        ("Dr. Priya Sharma", "General Medicine"),
        ("Dr. Rajesh Kumar", "General Medicine"),
        ("Dr. Anita Verma", "Pediatrics"),
        ("Dr. Suresh Patel", "Orthopedics"),
    ]
    rows = []
    for day_offset in range(7):
        d = date.today() - timedelta(days=day_offset)
        for name, spec in doctors:
            status = random.choices(["present", "absent", "leave", "half_day"], weights=[70, 15, 10, 5])[0]
            check_in = "09:00" if status in ("present", "half_day") else "—"
            check_out = "17:00" if status == "present" else ("13:00" if status == "half_day" else "—")
            rows.append({
                "Date": d, "Doctor": name, "Specialization": spec,
                "Status": status.replace("_", " ").title(),
                "Check In": check_in, "Check Out": check_out,
            })
    return pd.DataFrame(rows)


def _demo_diagnostics() -> pd.DataFrame:
    rows = []
    for test in DIAGNOSTIC_TESTS:
        available = random.random() > 0.15
        equipment = "Operational" if available else random.choice(["Under Maintenance", "Out of Order"])
        rows.append({
            "Test Name": test["name"], "Category": test["category"],
            "Available": "✅ Yes" if available else "❌ No",
            "Equipment Status": equipment,
            "Last Checked": (datetime.now() - timedelta(hours=random.randint(1, 72))).strftime("%Y-%m-%d %H:%M"),
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════
#  RENDER PAGE
# ══════════════════════════════════════════════════════════════

# ── Page Title ──
st.markdown(
    f"""
    <div class="page-title">{ICONS['facility']} Facility Details</div>
    <div class="page-subtitle">Comprehensive view of individual facility performance and resources</div>
    """,
    unsafe_allow_html=True,
)

def _get_all_facilities() -> list[dict]:
    """Fetch active facilities from database, with fallback to demo data."""
    try:
        from models.database import get_db_session
        from models.schema import Facility
        with get_db_session() as session:
            db_facs = session.query(Facility).filter(Facility.is_active == True).all()
            if db_facs:
                return [
                    {
                        "id": f.id,
                        "name": f.name,
                        "type": f.facility_type.value if hasattr(f.facility_type, "value") else str(f.facility_type),
                        "address": f.address or f"{f.name}, {f.district}",
                        "phone": f.phone or "N/A",
                        "capacity": f.total_capacity,
                        "lat": round(f.latitude, 2) if f.latitude else 26.85,
                        "lon": round(f.longitude, 2) if f.longitude else 80.95,
                    }
                    for f in db_facs
                ]
    except Exception:
        pass
    return DEMO_FACILITIES


# ── Facility Selector ──
facilities_list = _get_all_facilities()
facility_names = [f["name"] for f in facilities_list]

selected_name = st.selectbox(
    "Select Facility",
    options=facility_names,
    key="facility_selector",
)

facility = next((f for f in facilities_list if f["name"] == selected_name), facilities_list[0])

# ── Facility Profile Card ──
type_color = "#2563EB" if facility["type"] == "CHC" else "#6366F1"
st.markdown(
    f"""
    <div class="glass-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
            <div style="flex:1; min-width:250px;">
                <h3 style="font-size:22px; font-weight:700; color:#1E293B; margin:0 0 4px 0;">
                    {facility['name']}
                </h3>
                <div style="margin-bottom:16px;">
                    <span class="status-badge" style="background:{type_color}; color:white;">
                        {facility['type']}
                    </span>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:14px; color:#64748B;">
                    <div>📍 <strong>Address:</strong></div>
                    <div>{facility['address']}</div>
                    <div>📞 <strong>Phone:</strong></div>
                    <div>{facility['phone']}</div>
                    <div>🏗️ <strong>Capacity:</strong></div>
                    <div>{facility['capacity']} beds</div>
                    <div>📌 <strong>Coordinates:</strong></div>
                    <div>{facility['lat']}°N, {facility['lon']}°E</div>
                </div>
            </div>
            <div style="text-align:center; padding:16px 24px; background:linear-gradient(135deg, #EFF6FF, #DBEAFE);
                        border-radius:16px; min-width:120px;">
                <div style="font-size:11px; text-transform:uppercase; letter-spacing:1px;
                            color:#64748B; font-weight:600;">Facility ID</div>
                <div style="font-size:36px; font-weight:800; color:#2563EB; margin:4px 0;">
                    #{facility['id']:03d}
                </div>
                <div style="font-size:12px; color:#64748B;">Lucknow District</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Mini KPIs ──
random.seed(facility["id"])
stock_count = random.randint(12, 15)
bed_occ = random.randint(45, 90)
att_rate = random.randint(70, 98)
alert_count = random.randint(0, 5)
random.seed()

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("💊 Stock Items", stock_count, delta=f"{random.randint(-2,2):+d}")
with m2:
    st.metric("🛏️ Bed Occupancy", f"{bed_occ}%", delta=f"{random.uniform(-5,5):+.1f}%", delta_color="inverse")
with m3:
    st.metric("📋 Attendance Rate", f"{att_rate}%", delta=f"{random.uniform(-3,3):+.1f}%")
with m4:
    st.metric("🚨 Active Alerts", alert_count, delta=f"{random.randint(-2,1):+d}", delta_color="inverse")

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ── Tabs ──
tab_overview, tab_stock, tab_beds, tab_attendance, tab_diagnostics = st.tabs([
    "📊 Overview", "💊 Stock", "🛏️ Beds", "📋 Attendance", "🔬 Diagnostics"
])

# ── Overview Tab ──
with tab_overview:
    ov1, ov2 = st.columns([1, 1])

    with ov1:
        st.markdown(
            '<div class="section-header"><span class="header-icon">🎯</span> Health Score</div>',
            unsafe_allow_html=True,
        )
        health_score = round((att_rate * 0.3 + (100 - bed_occ) * 0.25 + random.uniform(60, 95) * 0.25 + max(0, 100 - alert_count * 15) * 0.2), 1)
        health_score = min(health_score, 100)

        score_color = "#22C55E" if health_score >= 75 else ("#F59E0B" if health_score >= 50 else "#EF4444")

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=health_score,
            number=dict(suffix="%", font=dict(size=42, color="#1E293B", family="Inter")),
            delta=dict(reference=75, increasing_color="#22C55E", decreasing_color="#EF4444"),
            gauge=dict(
                axis=dict(range=[0, 100], tickwidth=1, tickcolor="#E2E8F0"),
                bar=dict(color=score_color, thickness=0.3),
                bgcolor="rgba(0,0,0,0)",
                borderwidth=0,
                steps=[
                    dict(range=[0, 50], color="#FEE2E2"),
                    dict(range=[50, 75], color="#FEF3C7"),
                    dict(range=[75, 100], color="#DCFCE7"),
                ],
                threshold=dict(line=dict(color="#1E293B", width=3), thickness=0.8, value=health_score),
            ),
        ))
        fig_gauge.update_layout(
            height=280,
            margin=dict(l=20, r=20, t=30, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter"),
        )
        st.plotly_chart(fig_gauge, use_container_width=True, key="facility_health_gauge")

    with ov2:
        st.markdown(
            '<div class="section-header"><span class="header-icon">🚨</span> Recent Alerts</div>',
            unsafe_allow_html=True,
        )
        demo_alerts = [
            {"severity": "critical", "type": "Low Stock", "msg": "Paracetamol 500mg below reorder level", "time": "2h ago"},
            {"severity": "warning", "type": "Absenteeism", "msg": "1 doctor absent without notice", "time": "4h ago"},
            {"severity": "info", "type": "High Footfall", "msg": "OPD footfall 30% above average", "time": "6h ago"},
        ]
        for a in demo_alerts[:min(alert_count + 1, 3)]:
            sev = a["severity"]
            icon = {"critical": "🔴", "warning": "⚠️", "info": "ℹ️"}.get(sev, "ℹ️")
            st.markdown(
                f"""
                <div class="alert-card alert-{sev}">
                    <div class="alert-icon">{icon}</div>
                    <div class="alert-content">
                        <div class="alert-title">{a['type']}</div>
                        <div class="alert-message">{a['msg']}</div>
                        <div class="alert-time">{a['time']}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if alert_count == 0:
            st.markdown(
                """
                <div class="glass-card" style="text-align:center; padding:32px;">
                    <div style="font-size:36px; margin-bottom:8px;">✅</div>
                    <p style="font-weight:600; color:#166534;">No active alerts</p>
                    <p style="font-size:13px; color:#64748B;">This facility is operating within normal parameters.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ── Stock Tab ──
with tab_stock:
    st.markdown(
        '<div class="section-header"><span class="header-icon">💊</span> Medicine Inventory</div>',
        unsafe_allow_html=True,
    )
    df_stock = _demo_stock_items(selected_name)

    def _stock_status_color(val):
        if val == "Adequate":
            return "background-color: #DCFCE7; color: #166534; font-weight:600;"
        elif val == "Low":
            return "background-color: #FEF3C7; color: #92400E; font-weight:600;"
        else:
            return "background-color: #FEE2E2; color: #991B1B; font-weight:600;"

    styled = getattr(df_stock.style, "map", getattr(df_stock.style, "applymap", None))(_stock_status_color, subset=["Status"])
    st.dataframe(styled, use_container_width=True, height=500, hide_index=True, key="facility_stock_table")

# ── Beds Tab ──
with tab_beds:
    st.markdown(
        '<div class="section-header"><span class="header-icon">🛏️</span> Ward-wise Bed Status</div>',
        unsafe_allow_html=True,
    )
    bed_data = _demo_bed_status()

    for ward in bed_data:
        pct = ward["occupancy_pct"]
        bar_color = "#22C55E" if pct < 70 else ("#F59E0B" if pct < 85 else "#EF4444")
        bg_color = "#DCFCE7" if pct < 70 else ("#FEF3C7" if pct < 85 else "#FEE2E2")
        st.markdown(
            f"""
            <div class="glass-card" style="padding:18px 24px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <div>
                        <span style="font-size:20px;">{ward['icon']}</span>
                        <span style="font-size:16px; font-weight:600; color:#1E293B; margin-left:8px;">
                            {ward['ward']} Ward
                        </span>
                    </div>
                    <div style="font-size:14px; color:#64748B;">
                        <strong style="color:#1E293B;">{ward['occupied']}</strong> / {ward['total']} beds occupied
                        &nbsp;
                        <span class="status-badge" style="background:{bg_color}; color:{bar_color}; border:1px solid {bar_color};">
                            {pct}%
                        </span>
                    </div>
                </div>
                <div style="background:#F1F5F9; border-radius:8px; height:12px; overflow:hidden;">
                    <div style="background:{bar_color}; height:100%; width:{pct}%; border-radius:8px;
                                transition:width 0.6s ease;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── Attendance Tab ──
with tab_attendance:
    st.markdown(
        '<div class="section-header"><span class="header-icon">📋</span> Recent Attendance Records</div>',
        unsafe_allow_html=True,
    )
    df_att = _demo_attendance()

    def _att_status_color(val):
        colors = {
            "Present": "background-color: #DCFCE7; color: #166534; font-weight:600;",
            "Absent": "background-color: #FEE2E2; color: #991B1B; font-weight:600;",
            "Leave": "background-color: #DBEAFE; color: #1E40AF; font-weight:600;",
            "Half Day": "background-color: #FEF3C7; color: #92400E; font-weight:600;",
        }
        return colors.get(val, "")

    styled_att = getattr(df_att.style, "map", getattr(df_att.style, "applymap", None))(_att_status_color, subset=["Status"])
    st.dataframe(styled_att, use_container_width=True, height=450, hide_index=True, key="facility_attendance_table")

# ── Diagnostics Tab ──
with tab_diagnostics:
    st.markdown(
        '<div class="section-header"><span class="header-icon">🔬</span> Diagnostic Test Availability</div>',
        unsafe_allow_html=True,
    )
    df_diag = _demo_diagnostics()

    def _equip_color(val):
        if val == "Operational":
            return "background-color: #DCFCE7; color: #166534; font-weight:600;"
        elif val == "Under Maintenance":
            return "background-color: #FEF3C7; color: #92400E; font-weight:600;"
        else:
            return "background-color: #FEE2E2; color: #991B1B; font-weight:600;"

    styled_diag = getattr(df_diag.style, "map", getattr(df_diag.style, "applymap", None))(_equip_color, subset=["Equipment Status"])
    st.dataframe(styled_diag, use_container_width=True, height=500, hide_index=True, key="facility_diagnostics_table")
