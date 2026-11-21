"""
CareGrid AI — Map Service
=============================
Geospatial queries for the interactive facility map:
markers, redistribution routes, and nearest-facility lookups.

Usage:
    from services.map_service import MapService
    markers = MapService.get_facility_markers()
"""

from __future__ import annotations

import logging
import math
from typing import Any, Optional

from models.database import get_db_session
from models.schema import Alert, Facility, StockItem
from config.constants import AlertSeverity

logger = logging.getLogger(__name__)

# ── Haversine distance (fallback if utils.geo not available) ──
try:
    from utils.geo import haversine_distance
except ImportError:
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate great-circle distance between two lat/lon points (km).

        Args:
            lat1, lon1: Source coordinates in decimal degrees.
            lat2, lon2: Destination coordinates in decimal degrees.

        Returns:
            Distance in kilometres.
        """
        R = 6371  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))
        return R * c


class MapService:
    """Static service for geospatial facility data."""

    # ── Facility Markers ─────────────────────────────────────
    @staticmethod
    def get_facility_markers() -> list[dict[str, Any]]:
        """
        Generate map marker data for every active facility.

        Status colour logic:
            - **red** : any *critical* unresolved alert
            - **orange** : >2 unresolved alerts (no critical)
            - **green** : otherwise

        Returns:
            List of marker dicts with popup HTML.
        """
        with get_db_session() as session:
            facilities = (
                session.query(Facility)
                .filter(Facility.is_active == True)  # noqa: E712
                .all()
            )

            markers: list[dict[str, Any]] = []
            for fac in facilities:
                # Count unresolved alerts and check for critical
                alerts = (
                    session.query(Alert)
                    .filter(
                        Alert.facility_id == fac.id,
                        Alert.is_resolved == False,  # noqa: E712
                    )
                    .all()
                )
                alert_count = len(alerts)
                has_critical = any(
                    a.severity == AlertSeverity.CRITICAL for a in alerts
                )

                # Determine status colour
                if has_critical:
                    status_color = "red"
                elif alert_count > 2:
                    status_color = "orange"
                else:
                    status_color = "green"

                # Build popup HTML
                status_label = {
                    "green": "Healthy",
                    "orange": "Warning",
                    "red": "Critical",
                }[status_color]
                popup_html = (
                    f"<div style='font-family:Inter,sans-serif;min-width:180px;'>"
                    f"<h4 style='margin:0 0 6px 0;color:#1E293B;'>{fac.name}</h4>"
                    f"<p style='margin:2px 0;color:#64748B;font-size:12px;'>"
                    f"Type: {fac.facility_type.value if fac.facility_type else 'N/A'}</p>"
                    f"<p style='margin:2px 0;color:#64748B;font-size:12px;'>"
                    f"Status: <b style='color:{status_color};'>{status_label}</b></p>"
                    f"<p style='margin:2px 0;color:#64748B;font-size:12px;'>"
                    f"Active Alerts: {alert_count}</p>"
                    f"</div>"
                )

                markers.append(
                    {
                        "id": fac.id,
                        "name": fac.name,
                        "type": fac.facility_type.value if fac.facility_type else "",
                        "lat": fac.latitude,
                        "lon": fac.longitude,
                        "status_color": status_color,
                        "popup_html": popup_html,
                    }
                )

        return markers

    # ── Redistribution Routes ────────────────────────────────
    @staticmethod
    def get_redistribution_routes() -> list[dict[str, Any]]:
        """
        Find medicines where surplus and deficit facilities exist,
        and produce route data for map polylines.

        Returns:
            List of route dicts with source/dest coordinates.
        """
        with get_db_session() as session:
            # Get all distinct medicine names
            medicine_names = [
                r[0]
                for r in session.query(StockItem.medicine_name).distinct().all()
            ]

            routes: list[dict[str, Any]] = []

            for med in medicine_names:
                # Surplus facilities: stock > 2× reorder level
                surplus_items = (
                    session.query(StockItem, Facility)
                    .join(Facility, StockItem.facility_id == Facility.id)
                    .filter(
                        StockItem.medicine_name == med,
                        StockItem.current_stock > 2 * StockItem.reorder_level,
                    )
                    .all()
                )
                # Deficit facilities: stock < reorder level
                deficit_items = (
                    session.query(StockItem, Facility)
                    .join(Facility, StockItem.facility_id == Facility.id)
                    .filter(
                        StockItem.medicine_name == med,
                        StockItem.current_stock < StockItem.reorder_level,
                    )
                    .all()
                )

                if not surplus_items or not deficit_items:
                    continue

                # Match surplus to deficit, closest first
                remaining_surplus = [
                    {
                        "item": si,
                        "facility": sf,
                        "available": si.current_stock - si.reorder_level,
                    }
                    for si, sf in surplus_items
                ]

                for def_item, def_fac in deficit_items:
                    needed = def_item.reorder_level - def_item.current_stock
                    if needed <= 0:
                        continue

                    # Sort surplus by distance to deficit facility
                    remaining_surplus.sort(
                        key=lambda s: haversine_distance(
                            s["facility"].latitude,
                            s["facility"].longitude,
                            def_fac.latitude,
                            def_fac.longitude,
                        )
                    )

                    for surplus in remaining_surplus:
                        if surplus["available"] <= 0 or needed <= 0:
                            continue

                        transfer_qty = min(surplus["available"], needed)
                        distance = haversine_distance(
                            surplus["facility"].latitude,
                            surplus["facility"].longitude,
                            def_fac.latitude,
                            def_fac.longitude,
                        )

                        routes.append(
                            {
                                "source": surplus["facility"].name,
                                "destination": def_fac.name,
                                "medicine": med,
                                "quantity": transfer_qty,
                                "route_coords": [
                                    [surplus["facility"].latitude, surplus["facility"].longitude],
                                    [def_fac.latitude, def_fac.longitude],
                                ],
                            }
                        )

                        surplus["available"] -= transfer_qty
                        needed -= transfer_qty
                        if needed <= 0:
                            break

        return routes

    # ── Nearest Facility ─────────────────────────────────────
    @staticmethod
    def get_nearest_facility(lat: float, lon: float) -> dict[str, Any]:
        """
        Find the nearest active facility to a given coordinate.

        Args:
            lat: Query latitude.
            lon: Query longitude.

        Returns:
            Dict with facility info and distance_km.
        """
        with get_db_session() as session:
            facilities = (
                session.query(Facility)
                .filter(Facility.is_active == True)  # noqa: E712
                .all()
            )

            if not facilities:
                return {}

            nearest = None
            min_dist = float("inf")

            for fac in facilities:
                dist = haversine_distance(lat, lon, fac.latitude, fac.longitude)
                if dist < min_dist:
                    min_dist = dist
                    nearest = fac

            if nearest is None:
                return {}

            return {
                "id": nearest.id,
                "name": nearest.name,
                "type": nearest.facility_type.value if nearest.facility_type else "",
                "lat": nearest.latitude,
                "lon": nearest.longitude,
                "distance_km": round(min_dist, 2),
            }
