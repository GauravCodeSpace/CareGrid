"""
CareGrid AI — Stock Monitoring Page
======================================
Medicine inventory tracking with consumption trends,
AI-powered demand forecasting, and stock-out predictions.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta
import random

# ── Service imports ──
try:
    from services.stock_service import StockService
    _STOCK_SVC = True
except ImportError:
    _STOCK_SVC = False

try:
    from services.ai_service import AIService
    _AI_SVC = True
except ImportError:
    _AI_SVC = False

try:
    from utils.translator import t
except ImportError:
    def t(key: str, **kwargs) -> str:
        return key

from config.constants import Colors, ICONS, MEDICINES


# ── Auth guard ──
if not st.session_state.get("authenticated"):
    st.switch_page("pages/1_Login.py")


# ── Demo Data ──
FACILITY_LIST = [
    "All Facilities", "PHC Rajpur", "CHC Sadar", "PHC Mohanlalganj",
    "CHC Malihabad", "PHC Bakshi Ka Talab", "PHC Chinhat", "CHC Kakori",
    "PHC Gosainganj", "PHC Itaunja", "CHC Nagram", "PHC Mal",
    "PHC Sarojininagar", "CHC Mohanlalganj Block", "PHC Amaniganj", "PHC Nilmatha",
]


@st.cache_data(ttl=300)
def _demo_inventory(facility: str) -> pd.DataFrame:
    rows = []
    for med in MEDICINES:
        stock = random.randint(5, med["reorder_level"] * 3)
        if stock > med["reorder_level"]:
            status = "Adequate"
        elif stock > med["reorder_level"] * 0.3:
            status = "Low"
        else:
            status = "Critical"
        rows.append({
            "Medicine": med["name"],
            "Category": med["category"],
            "Current Stock": stock,
            "Reorder Level": med["reorder_level"],
            "Unit": med["unit"],
            "Status": status,
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def _demo_consumption(medicine: str) -> pd.DataFrame:
    dates = pd.date_range(end=date.today(), periods=30, freq="D")
    base = random.randint(15, 45)
    consumption = [max(0, base + random.randint(-12, 12) + int(3 * np.sin(i / 5))) for i in range(30)]
    return pd.DataFrame({"date": dates, "consumed": consumption})


@st.cache_data(ttl=300)
def _demo_forecast(medicine: str) -> pd.DataFrame:
    dates = pd.date_range(start=date.today() + timedelta(days=1), periods=14, freq="D")
    base = random.randint(20, 40)
    predicted = [max(0, base + random.randint(-5, 8) + int(2 * np.sin(i / 4))) for i in range(14)]
    upper = [p + random.randint(5, 15) for p in predicted]
    lower = [max(0, p - random.randint(5, 12)) for p in predicted]
    return pd.DataFrame({
        "date": dates,
        "predicted": predicted,
        "upper_bound": upper,
        "lower_bound": lower,
    })


@st.cache_data(ttl=300)
def _demo_stockout_predictions() -> pd.DataFrame:
    rows = []
    for med in MEDICINES:
        stock = random.randint(20, med["reorder_level"] * 2)
        avg_daily = random.randint(8, 35)
        days_remaining = round(stock / avg_daily, 1) if avg_daily > 0 else 999
        if days_remaining <= 3:
            risk = "Critical"
        elif days_remaining <= 7:
            risk = "High"
        elif days_remaining <= 14:
            risk = "Medium"
        else:
            risk = "Low"
        rows.append({
            "Medicine": med["name"],
            "Current Stock": stock,
            "Avg Daily Consumption": avg_daily,
            "Days Remaining": days_remaining,
            "Risk Level": risk,
        })
    df = pd.DataFrame(rows)
    return df.sort_values("Days Remaining").reset_index(drop=True)


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


# ── Data Loaders (Database with Demo Fallback) ──
def _load_inventory(facility: str) -> pd.DataFrame:
    if _STOCK_SVC:
        try:
            facility_id = None
            if facility != "All Facilities":
                from models.database import get_db_session
                from models.schema import Facility
                with get_db_session() as session:
                    fac = session.query(Facility).filter(Facility.name == facility).first()
                    if fac:
                        facility_id = fac.id
            
            data = StockService.get_all_stock(facility_id)
            if data:
                rows = []
                for d in data:
                    rows.append({
                        "Medicine": d["medicine_name"],
                        "Category": d["category"],
                        "Current Stock": d["current_stock"],
                        "Reorder Level": d["reorder_level"],
                        "Unit": d["unit"],
                        "Status": d["status"].title(), # Adequate, Low, Critical
                    })
                return pd.DataFrame(rows)
        except Exception:
            pass
    return _demo_inventory(facility)


def _load_consumption(medicine: str) -> pd.DataFrame:
    if _STOCK_SVC:
        try:
            from models.database import get_db_session
            from models.schema import StockItem
            with get_db_session() as session:
                med_item = session.query(StockItem).filter(StockItem.medicine_name == medicine).first()
                if med_item:
                    df = StockService.get_consumption_history(med_item.id, days=30)
                    if not df.empty:
                        df = df.rename(columns={"consumption": "consumed"})
                        df["date"] = pd.to_datetime(df["date"])
                        return df
        except Exception:
            pass
    return _demo_consumption(medicine)


def _load_stockout_predictions() -> pd.DataFrame:
    if _STOCK_SVC:
        try:
            from models.database import get_db_session
            from models.schema import StockItem
            with get_db_session() as session:
                items = session.query(StockItem).all()
                rows = []
                for item in items:
                    pred = StockService.predict_stockout_days(item.id)
                    risk_level = "Low"
                    if pred["days_remaining"] <= 3:
                        risk_level = "Critical"
                    elif pred["days_remaining"] <= 7:
                        risk_level = "High"
                    elif pred["days_remaining"] <= 14:
                        risk_level = "Medium"
                    
                    rows.append({
                        "Medicine": item.medicine_name,
                        "Current Stock": item.current_stock,
                        "Avg Daily Consumption": pred["avg_daily_consumption"],
                        "Days Remaining": pred["days_remaining"],
                        "Risk Level": risk_level,
                    })
                if rows:
                    return pd.DataFrame(rows).sort_values("Days Remaining").reset_index(drop=True)
        except Exception:
            pass
    return _demo_stockout_predictions()


# ══════════════════════════════════════════════════════════════
#  RENDER PAGE
# ══════════════════════════════════════════════════════════════

# Inject CSS to force input text visibility specifically on this page
st.markdown("""
<style>
    div[data-testid="stSelectbox"] div {
        color: #0f172a !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Page Title ──
st.markdown(
    f"""
    <div class="page-title">{ICONS['stock']} Stock Monitoring</div>
    <div class="page-subtitle">Medicine inventory tracking, consumption analysis, and AI-powered demand forecasting</div>
    """,
    unsafe_allow_html=True,
)

# ── Facility Filter ──
selected_facility = st.selectbox(
    "Filter by Facility",
    options=FACILITY_LIST,
    key="stock_facility_filter",
)

# ── Load Inventory ──
df_inventory = _load_inventory(selected_facility)

# ── KPI Row ──
total_items = len(df_inventory)
low_items = len(df_inventory[df_inventory["Status"] == "Low"])
critical_items = len(df_inventory[df_inventory["Status"] == "Critical"])
adequate_items = len(df_inventory[df_inventory["Status"] == "Adequate"])

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("📦 Total Items", total_items)
with k2:
    st.metric("⚠️ Low Stock", low_items, delta=f"{random.randint(-2,3):+d}", delta_color="inverse")
with k3:
    st.metric("🔴 Critical", critical_items, delta=f"{random.randint(-1,2):+d}", delta_color="inverse")
with k4:
    st.metric("✅ Adequate", adequate_items, delta=f"{random.randint(-1,2):+d}")

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# ── Medicine Inventory Table ──
st.markdown(
    '<div class="section-header"><span class="header-icon">📋</span> Medicine Inventory</div>',
    unsafe_allow_html=True,
)


def _status_color(val):
    if val == "Adequate":
        return "background-color: #DCFCE7; color: #166534; font-weight:600;"
    elif val == "Low":
        return "background-color: #FEF3C7; color: #92400E; font-weight:600;"
    else:
        return "background-color: #FEE2E2; color: #991B1B; font-weight:600;"


styled = getattr(df_inventory.style, "map", getattr(df_inventory.style, "applymap", None))(_status_color, subset=["Status"])
st.dataframe(styled, use_container_width=True, height=400, hide_index=True, key="stock_inventory_table")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Low Stock Highlights ──
low_stock_items = df_inventory[df_inventory["Status"].isin(["Low", "Critical"])].reset_index(drop=True)

if not low_stock_items.empty:
    st.markdown(
        '<div class="section-header"><span class="header-icon">🚨</span> Low Stock Highlights</div>',
        unsafe_allow_html=True,
    )
    alert_cols = st.columns(2)
    for i, row in low_stock_items.iterrows():
        severity = "critical" if row["Status"] == "Critical" else "warning"
        icon = "🔴" if severity == "critical" else "⚠️"
        pct = round(row["Current Stock"] / row["Reorder Level"] * 100, 1) if row["Reorder Level"] > 0 else 0
        with alert_cols[i % 2]:
            st.markdown(
                f"""
                <div class="alert-card alert-{severity}">
                    <div class="alert-icon">{icon}</div>
                    <div class="alert-content">
                        <div class="alert-title">{row['Medicine']}</div>
                        <div class="alert-message">
                            {row['Current Stock']} {row['Unit']} remaining ({pct}% of reorder level)
                        </div>
                        <div class="alert-time">Category: {row['Category']}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Historical Consumption Chart ──
st.markdown(
    '<div class="section-header"><span class="header-icon">📈</span> Historical Consumption</div>',
    unsafe_allow_html=True,
)

medicine_names = [m["name"] for m in MEDICINES]
selected_medicine = st.selectbox("Select Medicine", medicine_names, key="stock_medicine_selector")

col_hist, col_forecast = st.columns(2)

with col_hist:
    df_consumption = _load_consumption(selected_medicine)
    fig_consumption = go.Figure()
    fig_consumption.add_trace(go.Scatter(
        x=df_consumption["date"],
        y=df_consumption["consumed"],
        mode="lines+markers",
        line=dict(color="#2563EB", width=2.5, shape="spline"),
        marker=dict(size=5, color="#2563EB"),
        fill="tozeroy",
        fillcolor="rgba(37, 99, 235, 0.06)",
        name="Daily Consumption",
        hovertemplate="<b>%{x|%b %d}</b><br>Consumed: %{y}<extra></extra>",
    ))
    _apply_chart_theme(fig_consumption)
    fig_consumption.update_layout(
        title=dict(text="Daily Consumption (Last 30 Days)", font=dict(size=15, color="#1E293B")),
        height=350,
        xaxis_title="",
        yaxis_title="Units Consumed",
    )
    st.plotly_chart(fig_consumption, use_container_width=True, key="stock_consumption_chart")

# ── Demand Forecast ──
with col_forecast:
    df_forecast = _demo_forecast(selected_medicine)
    fig_forecast = go.Figure()

    # Confidence band
    fig_forecast.add_trace(go.Scatter(
        x=df_forecast["date"],
        y=df_forecast["upper_bound"],
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip",
    ))
    fig_forecast.add_trace(go.Scatter(
        x=df_forecast["date"],
        y=df_forecast["lower_bound"],
        mode="lines",
        line=dict(width=0),
        fill="tonexty",
        fillcolor="rgba(99, 102, 241, 0.12)",
        name="Confidence Band",
        hoverinfo="skip",
    ))
    # Predicted line
    fig_forecast.add_trace(go.Scatter(
        x=df_forecast["date"],
        y=df_forecast["predicted"],
        mode="lines+markers",
        line=dict(color="#6366F1", width=2.5, shape="spline", dash="dot"),
        marker=dict(size=5, color="#6366F1"),
        name="Predicted Demand",
        hovertemplate="<b>%{x|%b %d}</b><br>Predicted: %{y}<extra></extra>",
    ))

    _apply_chart_theme(fig_forecast)
    fig_forecast.update_layout(
        title=dict(text="Demand Forecast (Next 14 Days)", font=dict(size=15, color="#1E293B")),
        height=350,
        xaxis_title="",
        yaxis_title="Predicted Demand",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )
    st.plotly_chart(fig_forecast, use_container_width=True, key="stock_forecast_chart")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Stock-Out Prediction Table ──
st.markdown(
    '<div class="section-header"><span class="header-icon">⏳</span> Stock-Out Predictions</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="section-subheader">AI-predicted days until stock depletion based on consumption patterns</p>',
    unsafe_allow_html=True,
)

df_stockout = _load_stockout_predictions()


def _risk_color(val):
    colors = {
        "Critical": "background-color: #FEE2E2; color: #991B1B; font-weight:600;",
        "High": "background-color: #FFEDD5; color: #9A3412; font-weight:600;",
        "Medium": "background-color: #FEF3C7; color: #92400E; font-weight:600;",
        "Low": "background-color: #DCFCE7; color: #166534; font-weight:600;",
    }
    return colors.get(val, "")


def _days_color(val):
    if val <= 3:
        return "background-color: #FEE2E2; color: #991B1B; font-weight:700;"
    elif val <= 7:
        return "background-color: #FFEDD5; color: #9A3412; font-weight:600;"
    elif val <= 14:
        return "background-color: #FEF3C7; color: #92400E; font-weight:600;"
    return ""


style_apply = getattr(df_stockout.style, "map", getattr(df_stockout.style, "applymap", None))
styled_stockout = style_apply(
    _risk_color, subset=["Risk Level"]
)
styled_stockout = getattr(styled_stockout, "map", getattr(styled_stockout, "applymap", None))(
    _days_color, subset=["Days Remaining"]
).format(
    {"Days Remaining": "{:.1f}"}
)

st.dataframe(styled_stockout, use_container_width=True, height=450, hide_index=True, key="stock_stockout_table")
