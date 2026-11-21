"""
CareGrid AI — AI Service
==========================
Orchestrates all AI models: forecasting, risk scoring, redistribution.
Provides consolidated AI insights with explainable recommendations.

Every recommendation includes: Reason, Confidence, Suggested Action.

Usage:
    from services.ai_service import AIService
    predictions = AIService.get_stock_predictions()
    risks = AIService.get_risk_scores()
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd
from sqlalchemy import func

from config.constants import MEDICINES
from models.database import get_db_session
from models.schema import Facility, StockItem, StockLog

logger = logging.getLogger(__name__)


class AIService:
    """Service orchestrating all AI-powered analytics."""

    @staticmethod
    def get_stock_predictions(facility_id: Optional[int] = None) -> list[dict]:
        """
        Generate stock-out predictions for medicines.

        Args:
            facility_id: Optional filter. None = all facilities.

        Returns:
            List of prediction dicts with reason, confidence, suggested_action.
        """
        predictions = []

        with get_db_session() as session:
            query = session.query(StockItem, Facility).join(
                Facility, StockItem.facility_id == Facility.id
            )
            if facility_id:
                query = query.filter(StockItem.facility_id == facility_id)

            items = query.all()

            for item, facility in items:
                # Calculate average daily consumption from last 30 days
                end_date = date.today()
                start_date = end_date - timedelta(days=30)

                consumption = (
                    session.query(func.sum(func.abs(StockLog.quantity_change)))
                    .filter(
                        StockLog.stock_item_id == item.id,
                        StockLog.change_type == "consumed",
                        StockLog.timestamp >= start_date.isoformat(),
                    )
                    .scalar()
                ) or 0

                avg_daily = consumption / 30.0 if consumption > 0 else 0

                # Days remaining
                if avg_daily > 0:
                    days_remaining = item.current_stock / avg_daily
                else:
                    days_remaining = 999  # No consumption = no stockout

                # Risk level
                if days_remaining <= 3:
                    risk_level = "critical"
                    confidence = 92
                elif days_remaining <= 7:
                    risk_level = "warning"
                    confidence = 80
                elif days_remaining <= 14:
                    risk_level = "moderate"
                    confidence = 70
                else:
                    risk_level = "healthy"
                    confidence = 85

                # Reason
                if risk_level == "critical":
                    reason = (
                        f"{item.medicine_name} at {facility.name} has only "
                        f"{item.current_stock} {item.unit} remaining with avg daily "
                        f"consumption of {avg_daily:.0f}. Stock will run out in "
                        f"~{days_remaining:.0f} days."
                    )
                    action = (
                        f"URGENT: Restock {item.medicine_name} immediately. "
                        f"Need minimum {item.reorder_level} {item.unit}."
                    )
                elif risk_level == "warning":
                    reason = (
                        f"{item.medicine_name} stock is below reorder level. "
                        f"Current: {item.current_stock}, Reorder: {item.reorder_level}."
                    )
                    action = (
                        f"Order {item.reorder_level - item.current_stock} "
                        f"{item.unit} within 48 hours."
                    )
                elif risk_level == "moderate":
                    reason = (
                        f"{item.medicine_name} will need restocking within 2 weeks."
                    )
                    action = "Schedule restocking in weekly procurement cycle."
                else:
                    reason = f"{item.medicine_name} stock levels are adequate."
                    action = "No action needed. Continue routine monitoring."

                predictions.append({
                    "facility_id": facility.id,
                    "facility_name": facility.name,
                    "medicine": item.medicine_name,
                    "category": item.category,
                    "current_stock": item.current_stock,
                    "reorder_level": item.reorder_level,
                    "unit": item.unit,
                    "avg_daily_consumption": round(avg_daily, 1),
                    "days_remaining": round(days_remaining, 1),
                    "risk_level": risk_level,
                    "confidence": confidence,
                    "reason": reason,
                    "suggested_action": action,
                })

        # Sort by days_remaining ascending (most urgent first)
        predictions.sort(key=lambda x: x["days_remaining"])
        return predictions

    @staticmethod
    def get_demand_forecast(
        stock_item_id: int, days_ahead: int = 14
    ) -> dict:
        """
        Forecast future demand for a specific stock item using Linear Regression.

        Args:
            stock_item_id: StockItem ID.
            days_ahead: Number of days to forecast.

        Returns:
            Dict with dates, values, confidence_lower, confidence_upper.
        """
        try:
            from models.forecasting import DemandForecaster
        except ImportError:
            logger.error("Forecasting model not available")
            return {"dates": [], "values": [], "confidence_lower": [], "confidence_upper": []}

        with get_db_session() as session:
            # Get consumption history
            logs = (
                session.query(
                    func.date(StockLog.timestamp).label("date"),
                    func.sum(func.abs(StockLog.quantity_change)).label("quantity"),
                )
                .filter(
                    StockLog.stock_item_id == stock_item_id,
                    StockLog.change_type == "consumed",
                )
                .group_by(func.date(StockLog.timestamp))
                .order_by(func.date(StockLog.timestamp))
                .all()
            )

            if len(logs) < 7:
                return {
                    "dates": [],
                    "values": [],
                    "confidence_lower": [],
                    "confidence_upper": [],
                    "message": "Insufficient data for forecasting (need >= 7 days)",
                }

            df = pd.DataFrame(
                [{"date": row.date, "quantity": row.quantity} for row in logs]
            )

        # Fit and predict
        forecaster = DemandForecaster()
        forecaster.fit(df)
        return forecaster.predict(days_ahead)

    @staticmethod
    def get_redistribution_suggestions() -> list[dict]:
        """
        Get medicine redistribution recommendations.

        Returns:
            List of transfer suggestion dicts.
        """
        try:
            from models.redistribution import RedistributionEngine
        except ImportError:
            logger.error("Redistribution engine not available")
            return []

        engine = RedistributionEngine()
        return engine.calculate_transfers()

    @staticmethod
    def get_risk_scores() -> list[dict]:
        """
        Get risk scores for all facilities.

        Returns:
            List of risk score dicts sorted by overall_score descending.
        """
        try:
            from models.risk_scoring import RiskScorer
        except ImportError:
            logger.error("Risk scoring model not available")
            return []

        scorer = RiskScorer()
        return scorer.calculate_all_risks()

    @staticmethod
    def get_ai_recommendations() -> list[dict]:
        """
        Generate consolidated AI recommendations sorted by priority.

        Returns:
            List of recommendation dicts with category, priority, reason,
            confidence, and action.
        """
        recommendations = []

        # 1. Stock-out predictions (critical/warning only)
        try:
            predictions = AIService.get_stock_predictions()
            for pred in predictions:
                if pred["risk_level"] in ("critical", "warning"):
                    priority = 1 if pred["risk_level"] == "critical" else 2
                    recommendations.append({
                        "priority": priority,
                        "category": "Stock",
                        "icon": "💊",
                        "facility": pred["facility_name"],
                        "recommendation": (
                            f"{pred['medicine']} stock critically low — "
                            f"{pred['days_remaining']:.0f} days remaining"
                        ),
                        "reason": pred["reason"],
                        "confidence": pred["confidence"],
                        "action": pred["suggested_action"],
                    })
        except Exception as e:
            logger.error("Error getting stock predictions: %s", e)

        # 2. Risk scores (warning/critical only)
        try:
            risks = AIService.get_risk_scores()
            for risk in risks:
                if risk["risk_level"] in ("critical", "warning"):
                    priority = 1 if risk["risk_level"] == "critical" else 3
                    for rec in risk.get("recommendations", []):
                        recommendations.append({
                            "priority": priority,
                            "category": "Risk",
                            "icon": "⚠️",
                            "facility": risk["facility_name"],
                            "recommendation": rec,
                            "reason": (
                                f"Overall risk score: {risk['overall_score']}/100 "
                                f"(Stock: {risk['stock_score']}, "
                                f"Attendance: {risk['attendance_score']}, "
                                f"Beds: {risk['bed_score']}, "
                                f"Diagnostics: {risk['diagnostic_score']})"
                            ),
                            "confidence": max(60, 100 - int(risk["overall_score"] * 0.3)),
                            "action": f"Review {risk['facility_name']} operations",
                        })
        except Exception as e:
            logger.error("Error getting risk scores: %s", e)

        # 3. Redistribution suggestions
        try:
            transfers = AIService.get_redistribution_suggestions()
            for transfer in transfers[:10]:  # Top 10
                recommendations.append({
                    "priority": 2,
                    "category": "Redistribution",
                    "icon": "🔄",
                    "facility": transfer["destination_facility"],
                    "recommendation": (
                        f"Transfer {transfer['transfer_quantity']} units of "
                        f"{transfer['medicine']} from {transfer['source_facility']}"
                    ),
                    "reason": transfer["reason"],
                    "confidence": transfer["confidence"],
                    "action": transfer["suggested_action"],
                })
        except Exception as e:
            logger.error("Error getting redistribution suggestions: %s", e)

        # Sort by priority (1=highest)
        recommendations.sort(key=lambda x: x["priority"])
        return recommendations
