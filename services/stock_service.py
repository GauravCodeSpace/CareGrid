"""
CareGrid AI — Stock Service
===============================
Inventory management queries: stock levels, consumption history,
stock-out predictions, and facility-level summaries.

Usage:
    from services.stock_service import StockService
    low_items = StockService.get_low_stock_items()
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Optional

import pandas as pd
from sqlalchemy import func, cast, Date

from models.database import get_db_session
from models.schema import Facility, StockItem, StockLog
from config.constants import StockChangeType

logger = logging.getLogger(__name__)


class StockService:
    """Static service for medicine inventory operations."""

    # ── All Stock ────────────────────────────────────────────
    @staticmethod
    def get_all_stock(facility_id: Optional[int] = None) -> list[dict[str, Any]]:
        """
        Retrieve all stock items, optionally filtered by facility.

        Args:
            facility_id: If provided, filter to this facility only.

        Returns:
            List of stock-item dicts with facility_name and status.
        """
        with get_db_session() as session:
            query = (
                session.query(StockItem, Facility.name.label("facility_name"))
                .join(Facility, StockItem.facility_id == Facility.id)
            )
            if facility_id is not None:
                query = query.filter(StockItem.facility_id == facility_id)

            rows = query.order_by(Facility.name, StockItem.medicine_name).all()

            results = []
            for item, fac_name in rows:
                if item.current_stock == 0:
                    status = "critical"
                elif item.current_stock < item.reorder_level:
                    status = "low"
                else:
                    status = "adequate"

                results.append(
                    {
                        "id": item.id,
                        "facility_id": item.facility_id,
                        "facility_name": fac_name,
                        "medicine_name": item.medicine_name,
                        "category": item.category,
                        "current_stock": item.current_stock,
                        "unit": item.unit,
                        "reorder_level": item.reorder_level,
                        "last_restocked": (
                            item.last_restocked.isoformat()
                            if item.last_restocked
                            else None
                        ),
                        "status": status,
                    }
                )
        return results

    # ── Low Stock Items ──────────────────────────────────────
    @staticmethod
    def get_low_stock_items() -> list[dict[str, Any]]:
        """
        Items where current_stock < reorder_level.

        Returns:
            List of stock-item dicts with facility_name.
        """
        with get_db_session() as session:
            rows = (
                session.query(StockItem, Facility.name.label("facility_name"))
                .join(Facility, StockItem.facility_id == Facility.id)
                .filter(StockItem.current_stock < StockItem.reorder_level)
                .order_by(
                    (StockItem.current_stock - StockItem.reorder_level).asc()
                )
                .all()
            )

            results = []
            for item, fac_name in rows:
                status = "critical" if item.current_stock == 0 else "low"
                results.append(
                    {
                        "id": item.id,
                        "facility_id": item.facility_id,
                        "facility_name": fac_name,
                        "medicine_name": item.medicine_name,
                        "category": item.category,
                        "current_stock": item.current_stock,
                        "unit": item.unit,
                        "reorder_level": item.reorder_level,
                        "last_restocked": (
                            item.last_restocked.isoformat()
                            if item.last_restocked
                            else None
                        ),
                        "status": status,
                    }
                )
        return results

    # ── Stock by Facility ────────────────────────────────────
    @staticmethod
    def get_stock_by_facility(facility_id: int) -> list[dict[str, Any]]:
        """
        All stock items for a specific facility.

        Args:
            facility_id: Target facility ID.

        Returns:
            List of stock-item dicts.
        """
        return StockService.get_all_stock(facility_id=facility_id)

    # ── Consumption History ──────────────────────────────────
    @staticmethod
    def get_consumption_history(
        stock_item_id: int, days: int = 30
    ) -> pd.DataFrame:
        """
        Daily consumption for a stock item from StockLog.

        Args:
            stock_item_id: Target stock item.
            days: Number of days of history.

        Returns:
            DataFrame with columns ['date', 'consumption'].
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        with get_db_session() as session:
            rows = (
                session.query(
                    func.date(StockLog.timestamp).label("date"),
                    func.sum(func.abs(StockLog.quantity_change)).label("consumption"),
                )
                .filter(
                    StockLog.stock_item_id == stock_item_id,
                    StockLog.change_type == StockChangeType.CONSUMED,
                    StockLog.timestamp >= cutoff,
                )
                .group_by(func.date(StockLog.timestamp))
                .order_by(func.date(StockLog.timestamp))
                .all()
            )

        if not rows:
            return pd.DataFrame(columns=["date", "consumption"])

        return pd.DataFrame(
            [{"date": r.date, "consumption": int(r.consumption)} for r in rows]
        )

    # ── Stock Summary by Facility ────────────────────────────
    @staticmethod
    def get_stock_summary_by_facility() -> pd.DataFrame:
        """
        Per-facility summary: total items, low stock count, critical count.

        Returns:
            DataFrame with columns
            ['facility_name', 'total_items', 'low_stock_count', 'critical_count'].
        """
        with get_db_session() as session:
            rows = (
                session.query(
                    Facility.name.label("facility_name"),
                    func.count(StockItem.id).label("total_items"),
                    func.sum(
                        func.iif(
                            StockItem.current_stock < StockItem.reorder_level, 1, 0
                        )
                    ).label("low_stock_count"),
                    func.sum(
                        func.iif(StockItem.current_stock == 0, 1, 0)
                    ).label("critical_count"),
                )
                .join(StockItem, StockItem.facility_id == Facility.id)
                .group_by(Facility.name)
                .order_by(Facility.name)
                .all()
            )

        if not rows:
            return pd.DataFrame(
                columns=["facility_name", "total_items", "low_stock_count", "critical_count"]
            )

        return pd.DataFrame(
            [
                {
                    "facility_name": r.facility_name,
                    "total_items": r.total_items,
                    "low_stock_count": int(r.low_stock_count or 0),
                    "critical_count": int(r.critical_count or 0),
                }
                for r in rows
            ]
        )

    # ── Predict Stock-Out Days ───────────────────────────────
    @staticmethod
    def predict_stockout_days(stock_item_id: int) -> dict[str, Any]:
        """
        Estimate how many days until a stock item runs out.

        Formula:
            days_remaining = current_stock / avg_daily_consumption (30 days)

        Risk levels:
            - critical : < 3 days
            - warning  : < 7 days
            - healthy  : ≥ 7 days

        Args:
            stock_item_id: Target stock item ID.

        Returns:
            Dict with medicine, current_stock, avg_daily_consumption,
            days_remaining, and risk_level.
        """
        cutoff = datetime.utcnow() - timedelta(days=30)

        with get_db_session() as session:
            item = session.query(StockItem).filter(StockItem.id == stock_item_id).first()
            if item is None:
                return {
                    "medicine": "Unknown",
                    "current_stock": 0,
                    "avg_daily_consumption": 0,
                    "days_remaining": 0,
                    "risk_level": "critical",
                }

            # Sum of consumed quantities in last 30 days
            total_consumed = (
                session.query(func.sum(func.abs(StockLog.quantity_change)))
                .filter(
                    StockLog.stock_item_id == stock_item_id,
                    StockLog.change_type == StockChangeType.CONSUMED,
                    StockLog.timestamp >= cutoff,
                )
                .scalar()
                or 0
            )

            avg_daily = total_consumed / 30.0 if total_consumed > 0 else 0.0

            if avg_daily > 0:
                days_remaining = round(item.current_stock / avg_daily, 1)
            else:
                days_remaining = 999.0  # no consumption → no risk

            if days_remaining < 3:
                risk_level = "critical"
            elif days_remaining < 7:
                risk_level = "warning"
            else:
                risk_level = "healthy"

            return {
                "medicine": item.medicine_name,
                "current_stock": item.current_stock,
                "avg_daily_consumption": round(avg_daily, 2),
                "days_remaining": days_remaining,
                "risk_level": risk_level,
            }
