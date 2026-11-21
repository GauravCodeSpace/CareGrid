"""
CareGrid AI — Bed Availability Page
======================================
Ward-wise bed occupancy, facility heatmap, and trend analysis.
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

from config.constants import Colors, ICONS, WardType


# ── Auth guard ──
if not st.session_state.get("authenticated"):
    st.switch_page("pages/1_Login.py")


# ── Demo Data ──
FACILITIES = [
    "PHC Rajpur", "CHC Sadar", "PHC Mohanlalganj", "CHC Malihabad",
    "PHC Bakshi Ka Talab", "PHC Chinhat", "CHC Kakori", "PHC Gosainganj",
    "PHC Itaunja", "CHC Nagram", "PHC Mal", "PHC Sarojininagar",
    "CHC Mohanlalganj Block", "PHC Amaniganj", "PHC Nilmatha",
]

WARDS = [
    {"name": "General", "icon": "🛏️", "color": "#2563EB"},
    {"name": "ICU", "icon": "🫀", "color": "#EF4444"},
    {"name": "Maternity", "icon": "👶", "color": "#EC4899"},
    {"name": "Pediatric", "icon": "🧒", "color": "#8B5CF6"},
    {"name": "Emergency", "icon": "🚑", "color": "#F59E0B"},
]


@st.cache_data(ttl=300)
def _demo_district_summary() -> dict:
    total = random.randint(600, 800)
    occupied = random.randint(int(total * 0.55), int(total * 0.85))
    return {
        "total_beds": total,
        "occupied": occupied,
        "available": total - occupied,
        "occupancy_pct": round(occupied / total * 100, 1),
    }


@st.cache_data(ttl=300)
def _demo_ward_data() -> list[dict]:
    ward_data = []
    for w in WARDS:
        total = random.randint(60, 160)
        occupied = random.randint(int(total * 0.3), int(total * 0.95))
        ward_data.append({
            **w,
            "total": total,
            "occupied": occupied,
            "available": total - occupied,
            "occupancy_pct": round(occupied / total * 100, 1),
        })
    return ward_data


@st.cache_data(ttl=300)
def _demo_facility_bed_table() -> pd.DataFrame:
    rows = []
    for fac in FACILITIES:
        is_chc = "CHC" in fac
        total = random.randint(40, 80) if is_chc else random.randint(15, 35)
        occupied = random.randint(int(total * 0.3), int(total * 0.95))
        available = total - occupied
        occ_pct = round(occupied / total * 100, 1)
        if occ_pct >= 90:
            status = "Critical"
        elif occ_pct >= 75:
            status = "High"
        elif occ_pct >= 50:
            status = "Moderate"
        else:
            status = "Normal"
        rows.append({
            "Facility": fac,
            "Total Beds": total,
            "Occupied": occupied,
            "Available": available,
            "Occupancy %": occ_pct,
            "Status": status,
        })
    return pd.DataFrame(rows).sort_values("Occupancy %", ascending=False).reset_index(drop=True)


@st.cache_data(ttl=300)
def _demo_heatmap_data() -> pd.DataFrame:
    rows = []
    for fac in FACILITIES:
        for w in WARDS:
            occ = random.randint(20, 98)
            rows.append({"Facility": fac, "Ward": w["name"], "Occupancy": occ})
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def _demo_trend_data() -> pd.DataFrame:
    dates = pd.date_range(end=date.today(), periods=30, freq="D")
    base = random.randint(60, 75)
    occupancy = [min(98, max(30, base + random.randint(-8, 8) + int(3 * np.sin(i / 5)))) for i in range(30)]
    return pd.DataFrame({"date": dates, "occupancy": occupancy})


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
    <div class="page-title">{ICONS['beds']} Bed Availability</div>
    <div class="page-subtitle">Real-time bed occupancy monitoring across all wards and facilities</div>
    """,
    unsafe_allow_html=True,
)

# ── District Summary KPIs ──
summary = _demo_district_summary()

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("🏗️ Total Beds", summary["total_beds"])
with k2:
    st.metric("🔴 Occupied", summary["occupied"], delta=f"{random.randint(-5,8):+d} today", delta_color="inverse")
with k3:
    st.metric("🟢 Available", summary["available"], delta=f"{random.randint(-8,5):+d} today")
with k4:
    occ_pct = summary["occupancy_pct"]
    occ_delta = round(random.uniform(-3, 3), 1)
    st.metric("📊 Occupancy %", f"{occ_pct}%", delta=f"{occ_delta:+.1f}%", delta_color="inverse")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Ward-wise Cards ──
st.markdown(
    '<div class="section-header"><span class="header-icon">🏥</span> Ward-wise Occupancy</div>',
    unsafe_allow_html=True,
)

ward_data = _demo_ward_data()
ward_cols = st.columns(len(ward_data))

for i, ward in enumerate(ward_data):
    with ward_cols[i]:
        pct = ward["occupancy_pct"]
        if pct >= 85:
            status_color = "#EF4444"
            status_bg = "#FEE2E2"
            status_text = "Critical"
        elif pct >= 70:
            status_color = "#F59E0B"
            status_bg = "#FEF3C7"
            status_text = "High"
        else:
            status_color = "#22C55E"
            status_bg = "#DCFCE7"
            status_text = "Normal"

        st.markdown(
            f"""
            <div class="glass-card" style="text-align:center; padding:20px 16px; border-top:4px solid {ward['color']};">
                <div style="font-size:32px; margin-bottom:6px;">{ward['icon']}</div>
                <div style="font-size:14px; font-weight:700; color:#1E293B; margin-bottom:4px;">
                    {ward['name']}
                </div>
                <div style="font-size:28px; font-weight:800; color:{ward['color']}; margin:8px 0;">
                    {pct}%
                </div>
                <div style="background:#F1F5F9; border-radius:6px; height:8px; margin:8px 0; overflow:hidden;">
                    <div style="background:{status_color}; height:100%; width:{pct}%; border-radius:6px;
                                transition:width 0.6s ease;"></div>
                </div>
                <div style="font-size:12px; color:#64748B;">
                    {ward['occupied']} / {ward['total']} beds
                </div>
                <div style="margin-top:6px;">
                    <span class="status-badge" style="background:{status_bg}; color:{status_color}; font-size:10px;">
                        {status_text}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Facility Bed Status Table ──
st.markdown(
    '<div class="section-header"><span class="header-icon">📋</span> Facility-wise Bed Status</div>',
    unsafe_allow_html=True,
)

df_beds = _demo_facility_bed_table()


def _bed_status_color(val):
    colors = {
        "Critical": "background-color: #FEE2E2; color: #991B1B; font-weight:600;",
        "High": "background-color: #FFEDD5; color: #9A3412; font-weight:600;",
        "Moderate": "background-color: #FEF3C7; color: #92400E; font-weight:600;",
        "Normal": "background-color: #DCFCE7; color: #166534; font-weight:600;",
    }
    return colors.get(val, "")


def _occ_pct_color(val):
    if val >= 90:
        return "background-color: #FEE2E2; color: #991B1B; font-weight:700;"
    elif val >= 75:
        return "background-color: #FEF3C7; color: #92400E; font-weight:600;"
    return ""


style_apply = getattr(df_beds.style, "map", getattr(df_beds.style, "applymap", None))
styled = style_apply(
    _bed_status_color, subset=["Status"]
)
styled = getattr(styled, "map", getattr(styled, "applymap", None))(
    _occ_pct_color, subset=["Occupancy %"]
)

st.dataframe(styled, use_container_width=True, height=400, hide_index=True, key="beds_facility_table")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Heatmap & Trend ──
heatmap_col, trend_col = st.columns(2)

with heatmap_col:
    st.markdown(
        '<div class="section-header"><span class="header-icon">🗺️</span> Occupancy Heatmap</div>',
        unsafe_allow_html=True,
    )
    df_heatmap = _demo_heatmap_data()

    pivot = df_heatmap.pivot(index="Facility", columns="Ward", values="Occupancy")

    fig_heatmap = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[
            [0.0, "#DCFCE7"],
            [0.5, "#FEF3C7"],
            [0.75, "#FFEDD5"],
            [1.0, "#FEE2E2"],
        ],
        zmin=0,
        zmax=100,
        text=pivot.values,
        texttemplate="%{text}%",
        textfont=dict(size=10, family="Inter"),
        hovertemplate="<b>%{y}</b><br>%{x}: %{z}%<extra></extra>",
        colorbar=dict(
            title=dict(text="Occupancy %", font=dict(size=12)),
            thickness=12,
            len=0.9,
        ),
    ))

    fig_heatmap.update_layout(
        height=500,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=11),
        xaxis=dict(side="top"),
    )
    st.plotly_chart(fig_heatmap, use_container_width=True, key="beds_heatmap")

with trend_col:
    st.markdown(
        '<div class="section-header"><span class="header-icon">📈</span> Occupancy Trend</div>',
        unsafe_allow_html=True,
    )
    df_trend = _demo_trend_data()

    fig_trend = go.Figure()

    # Threshold zones
    fig_trend.add_hrect(y0=85, y1=100, fillcolor="rgba(239,68,68,0.06)", line_width=0)
    fig_trend.add_hrect(y0=70, y1=85, fillcolor="rgba(245,158,11,0.06)", line_width=0)

    # Threshold lines
    fig_trend.add_hline(y=85, line_dash="dash", line_color="#EF4444", line_width=1,
                        annotation_text="Critical (85%)", annotation_position="top left",
                        annotation_font=dict(size=10, color="#EF4444"))
    fig_trend.add_hline(y=70, line_dash="dash", line_color="#F59E0B", line_width=1,
                        annotation_text="Warning (70%)", annotation_position="bottom left",
                        annotation_font=dict(size=10, color="#F59E0B"))

    fig_trend.add_trace(go.Scatter(
        x=df_trend["date"],
        y=df_trend["occupancy"],
        mode="lines",
        line=dict(color="#2563EB", width=2.5, shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(37, 99, 235, 0.06)",
        name="Occupancy %",
        hovertemplate="<b>%{x|%b %d}</b><br>Occupancy: %{y}%<extra></extra>",
    ))

    _apply_chart_theme(fig_trend)
    fig_trend.update_layout(
        height=500,
        xaxis_title="",
        yaxis_title="Occupancy %",
        yaxis=dict(range=[0, 105]),
    )
    st.plotly_chart(fig_trend, use_container_width=True, key="beds_trend_chart")
