"""
CareGrid AI — Patient Footfall Analytics Page
================================================
Daily, weekly, and monthly patient footfall trends with
department breakdowns and facility comparisons.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta
import random

# ── Service imports ──
try:
    from services.dashboard_service import DashboardService
    _DASHBOARD_SVC = True
except ImportError:
    _DASHBOARD_SVC = False

try:
    from utils.translator import t
except ImportError:
    def t(key: str, **kwargs) -> str:
        return key

from config.constants import Colors, ICONS, DEPARTMENTS


# ── Auth guard ──
if not st.session_state.get("authenticated"):
    st.switch_page("pages/1_Login.py")


# ── Facility list ──
FACILITY_LIST = [
    "All Facilities", "PHC Rajpur", "CHC Sadar", "PHC Mohanlalganj",
    "CHC Malihabad", "PHC Bakshi Ka Talab", "PHC Chinhat", "CHC Kakori",
    "PHC Gosainganj", "PHC Itaunja", "CHC Nagram", "PHC Mal",
    "PHC Sarojininagar", "CHC Mohanlalganj Block", "PHC Amaniganj", "PHC Nilmatha",
]


# ── Demo Data ──
@st.cache_data(ttl=300)
def _demo_footfall_daily() -> pd.DataFrame:
    dates = pd.date_range(end=date.today(), periods=30, freq="D")
    rows = []
    for d in dates:
        is_weekend = d.weekday() >= 5
        base = random.randint(120, 180) if not is_weekend else random.randint(40, 80)
        opd = int(base * random.uniform(0.55, 0.65))
        ipd = int(base * random.uniform(0.15, 0.25))
        emergency = base - opd - ipd
        rows.append({
            "date": d, "total": base,
            "OPD": opd, "IPD": ipd, "Emergency": emergency,
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def _demo_footfall_weekly() -> pd.DataFrame:
    weeks = pd.date_range(end=date.today(), periods=12, freq="W-MON")
    rows = []
    for w in weeks:
        total = random.randint(800, 1400)
        opd = int(total * random.uniform(0.55, 0.65))
        ipd = int(total * random.uniform(0.15, 0.25))
        emergency = total - opd - ipd
        rows.append({
            "date": w, "total": total,
            "OPD": opd, "IPD": ipd, "Emergency": emergency,
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def _demo_footfall_monthly() -> pd.DataFrame:
    months = pd.date_range(end=date.today(), periods=6, freq="MS")
    rows = []
    for m in months:
        total = random.randint(3500, 5500)
        opd = int(total * random.uniform(0.55, 0.65))
        ipd = int(total * random.uniform(0.15, 0.25))
        emergency = total - opd - ipd
        rows.append({
            "date": m, "total": total,
            "OPD": opd, "IPD": ipd, "Emergency": emergency,
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def _demo_department_breakdown() -> pd.DataFrame:
    rows = []
    for dept in DEPARTMENTS:
        count = random.randint(50, 450)
        rows.append({"Department": dept, "Patients": count})
    return pd.DataFrame(rows).sort_values("Patients", ascending=False).reset_index(drop=True)


@st.cache_data(ttl=300)
def _demo_facility_comparison() -> pd.DataFrame:
    facilities = [f for f in FACILITY_LIST if f != "All Facilities"]
    rows = []
    for f in facilities:
        is_chc = "CHC" in f
        total = random.randint(800, 2000) if is_chc else random.randint(300, 1000)
        rows.append({"Facility": f, "Total Footfall": total})
    return pd.DataFrame(rows).sort_values("Total Footfall", ascending=True).reset_index(drop=True)


def _apply_chart_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(
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
        hoverlabel=dict(bgcolor="#1E293B", font_size=12, font_family="Inter", font_color="white"),
    )
    return fig


# ══════════════════════════════════════════════════════════════
#  RENDER PAGE
# ══════════════════════════════════════════════════════════════

# ── Page Title ──
st.markdown(
    f"""
    <div class="page-title">{ICONS['footfall']} Patient Footfall Analytics</div>
    <div class="page-subtitle">Track patient volumes across departments, facilities, and time periods</div>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar Filters ──
with st.sidebar:
    st.markdown(
        '<p style="color:rgba(255,255,255,0.5); font-size:11px; '
        'text-transform:uppercase; letter-spacing:1px;">Footfall Filters</p>',
        unsafe_allow_html=True,
    )
    selected_facility = st.selectbox(
        "Facility", FACILITY_LIST, key="footfall_facility_filter"
    )

# ── View Toggle ──
view_mode = st.radio(
    "View Period",
    ["Daily", "Weekly", "Monthly"],
    horizontal=True,
    key="footfall_view_mode",
)

# ── Load data based on view ──
if view_mode == "Daily":
    df_trend = _demo_footfall_daily()
    date_format = "%b %d"
elif view_mode == "Weekly":
    df_trend = _demo_footfall_weekly()
    date_format = "Week of %b %d"
else:
    df_trend = _demo_footfall_monthly()
    date_format = "%B %Y"

# ── KPI Row ──
total_patients = df_trend["total"].sum()
total_opd = df_trend["OPD"].sum()
total_ipd = df_trend["IPD"].sum()
total_emergency = df_trend["Emergency"].sum()

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("👥 Total Patients", f"{total_patients:,}", delta=f"+{random.randint(2,8)}% vs last period")
with k2:
    st.metric("🏥 OPD", f"{total_opd:,}", delta=f"+{random.randint(1,6)}%")
with k3:
    st.metric("🛏️ IPD", f"{total_ipd:,}", delta=f"{random.randint(-3,4):+d}%")
with k4:
    st.metric("🚑 Emergency", f"{total_emergency:,}", delta=f"{random.randint(-5,5):+d}%", delta_color="inverse")

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# ── Main Trend Chart ──
st.markdown(
    '<div class="section-header"><span class="header-icon">📈</span> Footfall Trend</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="color:#475569; font-size:13.5px; margin-top:-10px; margin-bottom:15px; font-weight: 500;">'
    '🔵 <b>OPD</b> (Outpatient), &nbsp;🟢 <b>IPD</b> (Inpatient), &nbsp;and &nbsp;🔴 <b>Emergency</b> patient volume trends.'
    '</p>',
    unsafe_allow_html=True,
)

fig_trend = go.Figure()

# Area traces for OPD, IPD, Emergency
fig_trend.add_trace(go.Scatter(
    x=df_trend["date"], y=df_trend["OPD"],
    mode="lines", name="OPD",
    line=dict(color="#2563EB", width=2, shape="spline"),
    fill="tozeroy", fillcolor="rgba(37, 99, 235, 0.08)",
    hovertemplate="<b>%{x|" + date_format + "}</b><br>OPD: %{y}<extra></extra>",
))
fig_trend.add_trace(go.Scatter(
    x=df_trend["date"], y=df_trend["IPD"],
    mode="lines", name="IPD",
    line=dict(color="#22C55E", width=2, shape="spline"),
    fill="tozeroy", fillcolor="rgba(34, 197, 94, 0.06)",
    hovertemplate="<b>%{x|" + date_format + "}</b><br>IPD: %{y}<extra></extra>",
))
fig_trend.add_trace(go.Scatter(
    x=df_trend["date"], y=df_trend["Emergency"],
    mode="lines", name="Emergency",
    line=dict(color="#EF4444", width=2, shape="spline"),
    fill="tozeroy", fillcolor="rgba(239, 68, 68, 0.06)",
    hovertemplate="<b>%{x|" + date_format + "}</b><br>Emergency: %{y}<extra></extra>",
))

_apply_chart_theme(fig_trend)
fig_trend.update_layout(
    height=400,
    xaxis_title="",
    yaxis_title="Patient Count",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig_trend, use_container_width=True, key="footfall_trend_chart")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Department Breakdown & Facility Comparison ──
col_dept, col_facility = st.columns(2)

with col_dept:
    st.markdown(
        '<div class="section-header"><span class="header-icon">🏢</span> Department Breakdown</div>',
        unsafe_allow_html=True,
    )
    df_dept = _demo_department_breakdown()

    dept_colors = [
        "#2563EB", "#6366F1", "#8B5CF6", "#EC4899",
        "#22C55E", "#F59E0B", "#EF4444", "#0EA5E9",
    ]

    fig_dept = go.Figure()
    fig_dept.add_trace(go.Bar(
        x=df_dept["Patients"],
        y=df_dept["Department"],
        orientation="h",
        marker=dict(
            color=dept_colors[:len(df_dept)],
            cornerradius=6,
        ),
        text=df_dept["Patients"],
        textposition="auto",
        textfont=dict(color="white", size=12, family="Inter"),
        hovertemplate="<b>%{y}</b><br>Patients: %{x}<extra></extra>",
    ))
    _apply_chart_theme(fig_dept)
    fig_dept.update_layout(
        height=400,
        xaxis_title="Patient Count",
        yaxis_title="",
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig_dept, use_container_width=True, key="footfall_dept_chart")

with col_facility:
    st.markdown(
        '<div class="section-header"><span class="header-icon">🏥</span> Facility Comparison</div>',
        unsafe_allow_html=True,
    )
    df_fac = _demo_facility_comparison()

    colors = ["#2563EB" if "CHC" in f else "#6366F1" for f in df_fac["Facility"]]

    fig_fac = go.Figure()
    fig_fac.add_trace(go.Bar(
        x=df_fac["Total Footfall"],
        y=df_fac["Facility"],
        orientation="h",
        marker=dict(color=colors, cornerradius=6),
        text=df_fac["Total Footfall"],
        textposition="auto",
        textfont=dict(color="white", size=11, family="Inter"),
        hovertemplate="<b>%{y}</b><br>Total: %{x:,}<extra></extra>",
    ))
    _apply_chart_theme(fig_fac)
    fig_fac.update_layout(
        height=400,
        xaxis_title="Total Footfall",
        yaxis_title="",
    )
    st.plotly_chart(fig_fac, use_container_width=True, key="footfall_facility_chart")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Peak Analysis Insights ──
st.markdown(
    '<div class="section-header"><span class="header-icon">📊</span> Peak Analysis Insights</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="color:#475569; font-size:13.5px; margin-top:-10px; margin-bottom:15px; font-weight: 500;">'
    'Busiest, average, and quietest patient traffic counts for peak resource planning.'
    '</p>',
    unsafe_allow_html=True,
)

if view_mode == "Daily":
    busiest_idx = df_trend["total"].idxmax()
    busiest_day = df_trend.loc[busiest_idx, "date"].strftime("%A, %b %d")
    busiest_count = df_trend.loc[busiest_idx, "total"]
    avg_daily = round(df_trend["total"].mean(), 1)
    quietest_idx = df_trend["total"].idxmin()
    quietest_day = df_trend.loc[quietest_idx, "date"].strftime("%A, %b %d")
    quietest_count = df_trend.loc[quietest_idx, "total"]
else:
    busiest_day = "Week 3"
    busiest_count = df_trend["total"].max()
    avg_daily = round(df_trend["total"].mean(), 1)
    quietest_day = "Week 1"
    quietest_count = df_trend["total"].min()

pc1, pc2, pc3 = st.columns(3)

with pc1:
    st.markdown(
        f"""
        <div class="glass-card" style="text-align:center; border-left:4px solid #22C55E;">
            <div style="font-size:28px; margin-bottom:8px;">📈</div>
            <div style="font-size:12px; text-transform:uppercase; letter-spacing:1px; color:#64748B; font-weight:600;">
                Busiest Period
            </div>
            <div style="font-size:22px; font-weight:800; color:#1E293B; margin:6px 0;">{busiest_day}</div>
            <div style="font-size:14px; color:#22C55E; font-weight:600;">{busiest_count:,} patients</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with pc2:
    st.markdown(
        f"""
        <div class="glass-card" style="text-align:center; border-left:4px solid #2563EB;">
            <div style="font-size:28px; margin-bottom:8px;">📊</div>
            <div style="font-size:12px; text-transform:uppercase; letter-spacing:1px; color:#64748B; font-weight:600;">
                Average per Period
            </div>
            <div style="font-size:22px; font-weight:800; color:#1E293B; margin:6px 0;">{avg_daily:,.0f}</div>
            <div style="font-size:14px; color:#2563EB; font-weight:600;">patients</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with pc3:
    st.markdown(
        f"""
        <div class="glass-card" style="text-align:center; border-left:4px solid #F59E0B;">
            <div style="font-size:28px; margin-bottom:8px;">📉</div>
            <div style="font-size:12px; text-transform:uppercase; letter-spacing:1px; color:#64748B; font-weight:600;">
                Quietest Period
            </div>
            <div style="font-size:22px; font-weight:800; color:#1E293B; margin:6px 0;">{quietest_day}</div>
            <div style="font-size:14px; color:#F59E0B; font-weight:600;">{quietest_count:,} patients</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
