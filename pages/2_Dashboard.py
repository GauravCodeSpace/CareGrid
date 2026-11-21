"""
CareGrid AI — Dashboard Page
===============================
Main monitoring dashboard with KPIs, charts, facility health table,
and latest alerts. All data sourced from DashboardService.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, timedelta
import random

# ── Service imports ──
try:
    from services.dashboard_service import DashboardService
    _DASHBOARD_SERVICE = True
except ImportError:
    _DASHBOARD_SERVICE = False

try:
    from utils.helper import format_number, format_percentage, section_header_html
    _HELPER_AVAILABLE = True
except ImportError:
    _HELPER_AVAILABLE = False

try:
    from utils.charts import (
        create_line_chart, create_bar_chart, apply_healthcare_theme
    )
    _CHARTS_AVAILABLE = True
except ImportError:
    _CHARTS_AVAILABLE = False

try:
    from utils.translator import t
except ImportError:
    def t(key: str, **kwargs) -> str:
        return key

from config.constants import Colors, ICONS, AlertSeverity


# ── Auth guard ──
if not st.session_state.get("authenticated"):
    st.switch_page("pages/1_Login.py")


# ── Demo Data Generation ──
@st.cache_data(ttl=300)
def _demo_kpis() -> dict:
    return {
        "total_facilities": 10,
        "active_alerts": random.randint(3, 12),
        "low_stock_items": random.randint(8, 25),
        "bed_occupancy_pct": round(random.uniform(62, 88), 1),
        "attendance_pct": round(random.uniform(78, 95), 1),
        "alerts_delta": random.randint(-3, 5),
        "stock_delta": random.randint(-5, 3),
        "bed_delta": round(random.uniform(-4, 4), 1),
        "attendance_delta": round(random.uniform(-3, 3), 1),
    }


@st.cache_data(ttl=300)
def _demo_footfall_trend() -> pd.DataFrame:
    dates = pd.date_range(end=date.today(), periods=30, freq="D")
    base = 280
    counts = [base + random.randint(-60, 80) + int(15 * (i / 30)) for i in range(30)]
    return pd.DataFrame({"date": dates, "total_footfall": counts})


@st.cache_data(ttl=300)
def _demo_stock_alerts() -> pd.DataFrame:
    facilities = [
        "PHC Rajpur", "CHC Sadar", "PHC Mohanlalganj", "CHC Malihabad",
        "PHC Bakshi Ka Talab", "PHC Chinhat", "CHC Kakori", "PHC Gosainganj",
    ]
    alerts = [random.randint(0, 8) for _ in facilities]
    return pd.DataFrame({"facility": facilities, "alerts": alerts})


@st.cache_data(ttl=300)
def _demo_facility_health() -> pd.DataFrame:
    facilities = [
        ("PHC Rajpur", "PHC"), ("CHC Sadar", "CHC"), ("PHC Mohanlalganj", "PHC"),
        ("CHC Malihabad", "CHC"), ("PHC Bakshi Ka Talab", "PHC"),
        ("PHC Chinhat", "PHC"), ("CHC Kakori", "CHC"), ("PHC Gosainganj", "PHC"),
        ("PHC Itaunja", "PHC"), ("CHC Nagram", "CHC"), ("PHC Mal", "PHC"),
        ("PHC Sarojininagar", "PHC"), ("CHC Mohanlalganj Block", "CHC"),
        ("PHC Amaniganj", "PHC"), ("PHC Nilmatha", "PHC"),
    ]
    rows = []
    for name, ftype in facilities:
        stock_pct = random.randint(45, 100)
        bed_occ = random.randint(30, 95)
        att = random.randint(65, 100)
        alert_count = random.randint(0, 6)
        health = round((stock_pct * 0.3 + (100 - bed_occ) * 0.25 + att * 0.25 + max(0, 100 - alert_count * 15) * 0.2), 1)
        stock_status = "Adequate" if stock_pct > 70 else ("Low" if stock_pct > 40 else "Critical")
        rows.append({
            "Facility": name, "Type": ftype,
            "Stock Status": stock_status,
            "Bed Occupancy": f"{bed_occ}%",
            "Attendance": f"{att}%",
            "Alerts": alert_count,
            "Health Score": min(health, 100),
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def _demo_alerts() -> list[dict]:
    alerts = [
        {"severity": "critical", "type": "Low Stock", "facility": "PHC Rajpur",
         "message": "Paracetamol 500mg stock critically low — only 45 tablets remaining",
         "time": "12 minutes ago"},
        {"severity": "critical", "type": "Stock Out", "facility": "CHC Sadar",
         "message": "Amoxicillin 250mg completely out of stock",
         "time": "28 minutes ago"},
        {"severity": "warning", "type": "High Absenteeism", "facility": "PHC Chinhat",
         "message": "3 out of 4 doctors absent today — attendance at 25%",
         "time": "1 hour ago"},
        {"severity": "warning", "type": "Bed Overcrowding", "facility": "CHC Malihabad",
         "message": "ICU ward at 95% capacity — only 1 bed available",
         "time": "2 hours ago"},
        {"severity": "info", "type": "High Footfall", "facility": "PHC Mohanlalganj",
         "message": "OPD footfall 40% above daily average — consider additional staff",
         "time": "3 hours ago"},
        {"severity": "warning", "type": "Low Stock", "facility": "PHC Gosainganj",
         "message": "Insulin (Regular) — 8 vials remaining, reorder level is 30",
         "time": "4 hours ago"},
    ]
    return alerts


# ── Load Data ──
def _load_kpis() -> dict:
    if _DASHBOARD_SERVICE:
        try:
            summary = DashboardService.get_kpi_summary()
            return {
                "total_facilities": summary.get("total_facilities", 15),
                "active_alerts": summary.get("active_alerts", 0),
                "low_stock_items": summary.get("low_stock_items", 0),
                "bed_occupancy_pct": summary.get("avg_bed_occupancy_pct", 0),
                "attendance_pct": summary.get("avg_attendance_pct", 0),
                "alerts_delta": 0,
                "stock_delta": 0,
                "bed_delta": 0.0,
                "attendance_delta": 0.0,
            }
        except Exception:
            pass
    return _demo_kpis()


def _load_footfall_trend() -> pd.DataFrame:
    if _DASHBOARD_SERVICE:
        try:
            df = DashboardService.get_footfall_trend(days=30)
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"])
                return df
        except Exception:
            pass
    return _demo_footfall_trend()


def _load_stock_alerts() -> pd.DataFrame:
    if _DASHBOARD_SERVICE:
        try:
            df = DashboardService.get_stock_alert_summary()
            if not df.empty:
                return df.rename(columns={"facility_name": "facility", "low_stock_count": "alerts"})
        except Exception:
            pass
    return _demo_stock_alerts()


def _load_facility_health() -> pd.DataFrame:
    if _DASHBOARD_SERVICE:
        try:
            data = DashboardService.get_facility_health_table()
            df = pd.DataFrame(data)
            df = df.rename(columns={
                "name": "Facility",
                "type": "Type",
                "stock_status": "Stock Status",
                "alert_count": "Alerts",
                "health_score": "Health Score",
            })
            df["Bed Occupancy"] = df["bed_occupancy_pct"].astype(str) + "%"
            df["Attendance"] = df["attendance_pct"].astype(str) + "%"
            return df[["Facility", "Type", "Stock Status", "Bed Occupancy", "Attendance", "Alerts", "Health Score"]]
        except Exception:
            pass
    return _demo_facility_health()


def _load_alerts() -> list[dict]:
    if _DASHBOARD_SERVICE:
        try:
            db_alerts = DashboardService.get_latest_alerts(limit=6)
            ui_alerts = []
            for a in db_alerts:
                ui_alerts.append({
                    "id": a.get("id"),
                    "severity": a.get("severity", "info").lower(),
                    "type": a.get("alert_type", "Alert"),
                    "facility": a.get("facility_name", ""),
                    "message": a.get("message", ""),
                    "time": a.get("created_at", "").split("T")[0], # Simple date formatting
                })
            return ui_alerts
        except Exception:
            pass
    return _demo_alerts()


# ── Plotly Healthcare Theme ──
def _apply_chart_theme(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#000000", family="Inter")),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#000000", size=12),
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(
            gridcolor="#cbd5e1", 
            showgrid=True, 
            zeroline=False,
            title_font=dict(color="#000000", size=12),
            tickfont=dict(color="#000000", size=11)
        ),
        yaxis=dict(
            gridcolor="#cbd5e1", 
            showgrid=True, 
            zeroline=False,
            title_font=dict(color="#000000", size=12),
            tickfont=dict(color="#000000", size=11)
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11, color="#000000"),
        ),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            font_size=12,
            font_family="Inter",
            font_color="white",
        ),
    )
    return fig


# ══════════════════════════════════════════════════════════════
#  RENDER PAGE
# ══════════════════════════════════════════════════════════════

# ── Sidebar Filters ──
with st.sidebar:
    st.markdown(
        '<p style="color:rgba(255,255,255,0.5); font-size:11px; '
        'text-transform:uppercase; letter-spacing:1px;">Dashboard Filters</p>',
        unsafe_allow_html=True,
    )
    date_range = st.date_input(
        "Date Range",
        value=(date.today() - timedelta(days=30), date.today()),
        key="dashboard_date_range",
    )

# ── Page Title ──
st.markdown(
    f"""
    <div class="page-title">{ICONS['dashboard']} {t("dashboard.title")}</div>
    <div class="page-subtitle">{t("dashboard.subtitle")}</div>
    """,
    unsafe_allow_html=True,
)

# ── KPI Row ──
kpis = _load_kpis()
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.metric(
        label=f"🏥 {t('dashboard.kpi_total_facilities')}",
        value=kpis.get("total_facilities", 15),
    )
with k2:
    st.metric(
        label=f"🚨 {t('dashboard.kpi_active_alerts')}",
        value=kpis.get("active_alerts", 0),
        delta=f"{kpis.get('alerts_delta', 0):+d} {t('common.today')}",
        delta_color="inverse",
    )
with k3:
    st.metric(
        label=f"⚠️ {t('dashboard.kpi_stock_critical')}",
        value=kpis.get("low_stock_items", 0),
        delta=f"{kpis.get('stock_delta', 0):+d} {t('common.today')}",
        delta_color="inverse",
    )
with k4:
    st.metric(
        label=f"🛏️ {t('dashboard.kpi_bed_occupancy')}",
        value=f"{kpis.get('bed_occupancy_pct', 0)}%",
        delta=f"{kpis.get('bed_delta', 0):+.1f}%",
        delta_color="inverse",
    )
with k5:
    st.metric(
        label=f"📋 {t('attendance.attendance_rate')}",
        value=f"{kpis.get('attendance_pct', 0)}%",
        delta=f"{kpis.get('attendance_delta', 0):+.1f}%",
    )

st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)

# ── Charts Row ──
chart_left, chart_right = st.columns(2)

with chart_left:
    st.markdown(
        f'<div class="section-header"><span class="header-icon">📈</span> {t("footfall.daily_trend")}</div>',
        unsafe_allow_html=True,
    )
    df_footfall = _load_footfall_trend()

    fig_footfall = go.Figure()
    fig_footfall.add_trace(go.Scatter(
        x=df_footfall["date"],
        y=df_footfall["total_footfall"],
        mode="lines",
        line=dict(color="#2563EB", width=2.5, shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(37, 99, 235, 0.08)",
        name="Patients",
        hovertemplate="<b style='color: #FF0000; font-size: 14px;'>%{x|%b %d}</b><br>"
                  "<span style='color: #FF0000; font-size: 14px;'>Patients: %{y}</span><extra></extra>",
    ))
    _apply_chart_theme(fig_footfall)
    fig_footfall.update_layout(
        height=350,
        xaxis_title="",
        yaxis_title="Patient Count",
    )
    st.plotly_chart(fig_footfall, use_container_width=True, key="dash_footfall_chart")

with chart_right:
    st.markdown(
        f'<div class="section-header"><span class="header-icon">💊</span> {t("dashboard.section_stock_summary")}</div>',
        unsafe_allow_html=True,
    )
    df_stock_alerts = _load_stock_alerts()

    colors = [
        "#EF4444" if v >= 5 else ("#F59E0B" if v >= 3 else "#22C55E")
        for v in df_stock_alerts["alerts"]
    ]

    fig_stock = go.Figure()
    fig_stock.add_trace(go.Bar(
        x=df_stock_alerts["alerts"],
        y=df_stock_alerts["facility"],
        orientation="h",
        marker=dict(color=colors, cornerradius=6),
        text=df_stock_alerts["alerts"],
        textposition="auto",
        textfont=dict(color="white", size=12, family="Inter"),
        hovertemplate="<span style='color: #FF0000; font-size: 14px;'>Patients: %{y}</span><extra></extra>",
    ))
    _apply_chart_theme(fig_stock)
    fig_stock.update_layout(
        height=350,
        xaxis_title="Number of Alerts",
        yaxis_title="",
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig_stock, use_container_width=True, key="dash_stock_alerts_chart")

st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)

# ── Facility Health Table ──
st.markdown(
    f'<div class="section-header"><span class="header-icon">🏥</span> {t("dashboard.section_facility_overview")}</div>',
    unsafe_allow_html=True,
)

df_health = _load_facility_health()

# Color coding for Health Score
def _health_color(score):
    if score >= 75:
        return "background-color: #DCFCE7; color: #166534; font-weight:600;"
    elif score >= 50:
        return "background-color: #FEF3C7; color: #92400E; font-weight:600;"
    else:
        return "background-color: #FEE2E2; color: #991B1B; font-weight:600;"


def _stock_color(status):
    if status == "Adequate":
        return "background-color: #DCFCE7; color: #166534; font-weight:600;"
    elif status == "Low":
        return "background-color: #FEF3C7; color: #92400E; font-weight:600;"
    else:
        return "background-color: #FEE2E2; color: #991B1B; font-weight:600;"


# Use Styler.map (pandas >= 2.1) or Styler.applymap (pandas < 2.1)
style_apply = getattr(df_health.style, "map", getattr(df_health.style, "applymap", None))
styled_df = style_apply(
    _health_color, subset=["Health Score"]
)
styled_df = getattr(styled_df, "map", getattr(styled_df, "applymap", None))(
    _stock_color, subset=["Stock Status"]
).format(
    {"Health Score": "{:.1f}"}
)

st.dataframe(
    styled_df,
    use_container_width=True,
    height=450,
    hide_index=True,
    key="dash_facility_health_table",
)

st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)

# ── Latest Alerts ──
st.markdown(
    f'<div class="section-header"><span class="header-icon">🚨</span> {t("dashboard.section_alerts")}</div>',
    unsafe_allow_html=True,
)

alerts = _load_alerts()

severity_icons = {
    "critical": "🔴",
    "warning": "⚠️",
    "info": "ℹ️",
}

alert_cols = st.columns(2)

for i, alert in enumerate(alerts):
    with alert_cols[i % 2]:
        severity = alert.get("severity", "info")
        icon = severity_icons.get(severity, "ℹ️")
        alert_id = alert.get("id")

        st.markdown(
            f"""
            <div class="alert-card alert-{severity}">
                <div class="alert-icon">{icon}</div>
                <div class="alert-content">
                    <div class="alert-title">{alert.get('type', 'Alert')} — {alert.get('facility', '')}</div>
                    <div class="alert-message">{alert.get('message', '')}</div>
                    <div class="alert-time">{alert.get('time', '')}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Resolve button — only show for real DB alerts (with id)
        if alert_id is not None:
            if st.button(f"✅ Resolve", key=f"resolve_alert_{alert_id}"):
                try:
                    DashboardService.resolve_alert(alert_id)
                    st.success(f"Alert resolved successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to resolve alert: {e}")
