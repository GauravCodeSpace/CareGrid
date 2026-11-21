"""
CareGrid AI — AI Insights Page
================================
The crown jewel: Explainable AI predictions, demand forecasting,
redistribution recommendations, risk assessment, and consolidated insights.

Every AI output shows: Reason, Confidence, Suggested Action.
"""

import streamlit as st
import pandas as pd
from datetime import date

from utils.auth import require_auth
from utils.helper import format_number, section_header_html, status_badge_html


def _render_prediction_card(pred: dict) -> None:
    """Render a single stock prediction card."""
    risk = pred["risk_level"]
    colors = {"critical": "#EF4444", "warning": "#F59E0B", "moderate": "#3B82F6", "healthy": "#22C55E"}
    bg_colors = {"critical": "#FEF2F2", "warning": "#FFFBEB", "moderate": "#EFF6FF", "healthy": "#F0FDF4"}
    icons = {"critical": "🔴", "warning": "🟡", "moderate": "🔵", "healthy": "🟢"}

    color = colors.get(risk, "#64748B")
    bg = bg_colors.get(risk, "#F8FAFC")
    icon = icons.get(risk, "⚪")

    st.markdown(
        f"""<div style="background:{bg};border-left:4px solid {color};border-radius:12px;
        padding:16px 20px;margin-bottom:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span style="font-size:14px;font-weight:600;color:#1E293B;">
                        {icon} {pred['medicine']}
                    </span>
                    <span style="font-size:11px;color:#64748B;margin-left:8px;">
                        {pred['facility_name']}
                    </span>
                </div>
                <span class="status-badge status-{risk}">{risk.upper()}</span>
            </div>
            <div style="margin-top:10px;font-size:13px;color:#475569;">
                <strong>📦 Stock:</strong> {pred['current_stock']} {pred.get('unit','')} |
                <strong>📊 Avg Daily:</strong> {pred['avg_daily_consumption']}/day |
                <strong>⏳ Days Left:</strong> {pred['days_remaining']:.0f}
            </div>
            <div style="margin-top:8px;padding:10px;background:rgba(255,255,255,0.6);border-radius:8px;">
                <div style="font-size:12px;color:#64748B;font-weight:500;">💡 REASON</div>
                <div style="font-size:12px;color:#1E293B;margin-top:2px;">{pred['reason']}</div>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;">
                <span style="font-size:12px;color:#64748B;">
                    Confidence: <strong style="color:{color};">{pred['confidence']}%</strong>
                </span>
                <span style="font-size:12px;color:#2563EB;font-weight:500;">
                    ✅ {pred['suggested_action'][:80]}{'...' if len(pred.get('suggested_action','')) > 80 else ''}
                </span>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def _render_recommendation_card(rec: dict) -> None:
    """Render a single AI recommendation card."""
    priority_colors = {1: "#EF4444", 2: "#F59E0B", 3: "#3B82F6"}
    priority_labels = {1: "HIGH", 2: "MEDIUM", 3: "LOW"}
    color = priority_colors.get(rec["priority"], "#64748B")
    label = priority_labels.get(rec["priority"], "INFO")

    st.markdown(
        f"""<div class="glass-card" style="border-left:4px solid {color};">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="font-size:15px;font-weight:600;color:#1E293B;">
                    {rec.get('icon','📌')} {rec['category']}
                </span>
                <span style="background:{color};color:white;padding:3px 10px;border-radius:12px;
                font-size:10px;font-weight:700;letter-spacing:0.5px;">{label}</span>
            </div>
            <div style="font-size:13px;color:#64748B;margin-bottom:6px;">
                🏥 {rec['facility']}
            </div>
            <div style="font-size:14px;color:#1E293B;font-weight:500;margin-bottom:10px;">
                {rec['recommendation']}
            </div>
            <div style="background:#F8FAFC;border-radius:8px;padding:10px;font-size:12px;">
                <div><strong>Reason:</strong> {rec['reason']}</div>
                <div style="margin-top:4px;"><strong>Confidence:</strong> {rec['confidence']}%</div>
                <div style="margin-top:4px;"><strong>Action:</strong> {rec['action']}</div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_page() -> None:
    """Render the AI Insights page."""
    if not require_auth():
        return

    st.markdown(
        '<div class="page-title">🤖 AI Insights</div>'
        '<div class="page-subtitle">Explainable AI-powered predictions, forecasting, and recommendations</div>',
        unsafe_allow_html=True,
    )

    try:
        from services.ai_service import AIService
    except ImportError:
        st.error("AI service not available.")
        return

    # ── Tabs ──
    tab_pred, tab_forecast, tab_redist, tab_risk, tab_recs = st.tabs([
        "🔮 Predictions", "📈 Forecasting", "🔄 Redistribution",
        "⚠️ Risk Assessment", "💡 Recommendations",
    ])

    # ════════════════════════════════════════════════
    # PREDICTIONS TAB
    # ════════════════════════════════════════════════
    with tab_pred:
        st.markdown(section_header_html("🔮", "Stock-Out Predictions"), unsafe_allow_html=True)
        st.caption("AI predicts when medicine stock will run out based on consumption patterns.")

        with st.spinner("Analyzing stock levels..."):
            try:
                predictions = AIService.get_stock_predictions()
            except Exception as e:
                st.error(f"Error loading predictions: {e}")
                predictions = []

        if predictions:
            # Filter controls
            risk_filter = st.multiselect(
                "Filter by Risk Level",
                ["critical", "warning", "moderate", "healthy"],
                default=["critical", "warning"],
                key="pred_risk_filter",
            )
            filtered = [p for p in predictions if p["risk_level"] in risk_filter]

            # Summary
            c1, c2, c3 = st.columns(3)
            critical_count = len([p for p in predictions if p["risk_level"] == "critical"])
            warning_count = len([p for p in predictions if p["risk_level"] == "warning"])
            with c1:
                st.metric("🔴 Critical", critical_count)
            with c2:
                st.metric("🟡 Warning", warning_count)
            with c3:
                st.metric("📦 Total Analyzed", len(predictions))

            st.markdown("<br>", unsafe_allow_html=True)

            for pred in filtered[:20]:
                _render_prediction_card(pred)
        else:
            st.info("No prediction data available. Run the data seeder first.")

    # ════════════════════════════════════════════════
    # FORECASTING TAB
    # ════════════════════════════════════════════════
    with tab_forecast:
        st.markdown(section_header_html("📈", "Demand Forecasting"), unsafe_allow_html=True)
        st.caption("Linear Regression-based forecast with confidence intervals.")

        from models.database import get_db_session
        from models.schema import StockItem, Facility

        with get_db_session() as session:
            items = (
                session.query(StockItem, Facility)
                .join(Facility, StockItem.facility_id == Facility.id)
                .all()
            )
            item_options = {
                f"{facility.name} — {item.medicine_name}": item.id
                for item, facility in items
            }

        if item_options:
            selected_item = st.selectbox(
                "Select Medicine", options=list(item_options.keys()),
                key="forecast_item_select",
            )
            item_id = item_options[selected_item]

            days_ahead = st.slider("Forecast Days Ahead", 7, 30, 14, key="forecast_days")

            if st.button("🔮 Generate Forecast", key="forecast_btn"):
                with st.spinner("Running Linear Regression model..."):
                    try:
                        forecast = AIService.get_demand_forecast(item_id, days_ahead)

                        if forecast.get("dates"):
                            import plotly.graph_objects as go
                            fig = go.Figure()

                            # Confidence band
                            fig.add_trace(go.Scatter(
                                x=forecast["dates"] + forecast["dates"][::-1],
                                y=forecast["confidence_upper"] + forecast["confidence_lower"][::-1],
                                fill="toself",
                                fillcolor="rgba(37, 99, 235, 0.1)",
                                line=dict(color="rgba(37, 99, 235, 0)"),
                                name="Confidence Interval",
                                showlegend=True,
                            ))

                            # Prediction line
                            fig.add_trace(go.Scatter(
                                x=forecast["dates"],
                                y=forecast["values"],
                                mode="lines+markers",
                                line=dict(color="#2563EB", width=3),
                                marker=dict(size=6),
                                name="Predicted Demand",
                            ))

                            fig.update_layout(
                                title=f"Demand Forecast — {selected_item}",
                                xaxis_title="Date",
                                yaxis_title="Predicted Consumption",
                                height=450,
                                template="plotly_white",
                                font=dict(family="Inter"),
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning(forecast.get("message", "Insufficient data for forecasting."))
                    except Exception as e:
                        st.error(f"Forecasting error: {e}")
        else:
            st.info("No stock items available.")

    # ════════════════════════════════════════════════
    # REDISTRIBUTION TAB
    # ════════════════════════════════════════════════
    with tab_redist:
        st.markdown(section_header_html("🔄", "Medicine Redistribution Suggestions"), unsafe_allow_html=True)
        st.caption("AI identifies surplus and deficit facilities and recommends optimal transfers.")

        with st.spinner("Analyzing redistribution opportunities..."):
            try:
                transfers = AIService.get_redistribution_suggestions()
            except Exception as e:
                st.error(f"Error: {e}")
                transfers = []

        if transfers:
            st.metric("📋 Transfer Suggestions", len(transfers))
            st.markdown("<br>", unsafe_allow_html=True)

            for i, t in enumerate(transfers[:15]):
                st.markdown(
                    f"""<div class="glass-card" style="border-left:4px solid #2563EB;">
                        <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
                            <span style="font-size:20px;">🏥</span>
                            <span style="font-weight:600;color:#1E293B;">{t['source_facility']}</span>
                            <span style="font-size:20px;">→</span>
                            <span style="font-weight:600;color:#2563EB;">{t['destination_facility']}</span>
                        </div>
                        <div style="display:flex;gap:24px;font-size:13px;color:#475569;margin-bottom:10px;">
                            <span>💊 <strong>{t['medicine']}</strong></span>
                            <span>📦 <strong>{t['transfer_quantity']}</strong> units</span>
                            <span>📍 <strong>{t['distance_km']}</strong> km</span>
                        </div>
                        <div style="background:#F8FAFC;border-radius:8px;padding:10px;font-size:12px;">
                            <div><strong>Reason:</strong> {t['reason']}</div>
                            <div style="margin-top:4px;">
                                <strong>Confidence:</strong> {t['confidence']}% |
                                <strong>Action:</strong> {t['suggested_action'][:100]}
                            </div>
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.success("✅ No redistribution needed — stock levels are balanced across facilities.")

    # ════════════════════════════════════════════════
    # RISK ASSESSMENT TAB
    # ════════════════════════════════════════════════
    with tab_risk:
        st.markdown(section_header_html("⚠️", "Facility Risk Assessment"), unsafe_allow_html=True)
        st.caption("Weighted risk scores: Stock (30%), Attendance (25%), Beds (25%), Diagnostics (20%)")

        with st.spinner("Calculating risk scores..."):
            try:
                risks = AIService.get_risk_scores()
            except Exception as e:
                st.error(f"Error: {e}")
                risks = []

        if risks:
            # Risk ranking table
            risk_df = pd.DataFrame([{
                "Facility": r["facility_name"],
                "Overall Score": r["overall_score"],
                "Stock": r["stock_score"],
                "Attendance": r["attendance_score"],
                "Beds": r["bed_score"],
                "Diagnostics": r["diagnostic_score"],
                "Risk Level": r["risk_level"].upper(),
            } for r in risks])

            st.dataframe(
                risk_df.style.background_gradient(subset=["Overall Score"], cmap="RdYlGn_r", vmin=0, vmax=100),
                use_container_width=True,
                hide_index=True,
            )

            # Risk gauges for top 4
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(section_header_html("📊", "Top Risk Facilities"), unsafe_allow_html=True)

            cols = st.columns(min(4, len(risks)))
            for i, risk in enumerate(risks[:4]):
                with cols[i]:
                    try:
                        from utils.charts import create_gauge_chart
                        fig = create_gauge_chart(
                            value=risk["overall_score"],
                            max_val=100,
                            title=risk["facility_name"][:20],
                            ranges=[
                                (0, 30, "#DCFCE7"),
                                (30, 50, "#FEF3C7"),
                                (50, 75, "#FED7AA"),
                                (75, 100, "#FEE2E2"),
                            ],
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception:
                        st.metric(risk["facility_name"][:20], f"{risk['overall_score']}/100")

                    # Recommendations
                    for rec in risk.get("recommendations", [])[:2]:
                        st.caption(f"• {rec}")
        else:
            st.info("No risk data available.")

    # ════════════════════════════════════════════════
    # RECOMMENDATIONS TAB
    # ════════════════════════════════════════════════
    with tab_recs:
        st.markdown(section_header_html("💡", "AI Recommendations"), unsafe_allow_html=True)
        st.caption("Consolidated, priority-sorted actionable recommendations from all AI modules.")

        with st.spinner("Generating recommendations..."):
            try:
                recommendations = AIService.get_ai_recommendations()
            except Exception as e:
                st.error(f"Error: {e}")
                recommendations = []

        if recommendations:
            c1, c2, c3 = st.columns(3)
            high = len([r for r in recommendations if r["priority"] == 1])
            med = len([r for r in recommendations if r["priority"] == 2])
            low = len([r for r in recommendations if r["priority"] == 3])
            with c1:
                st.metric("🔴 High Priority", high)
            with c2:
                st.metric("🟡 Medium Priority", med)
            with c3:
                st.metric("🔵 Low Priority", low)

            st.markdown("<br>", unsafe_allow_html=True)

            for rec in recommendations[:25]:
                _render_recommendation_card(rec)
        else:
            st.success("✅ No critical recommendations — all systems operating normally.")


# ── Page Entry Point ──
render_page()
