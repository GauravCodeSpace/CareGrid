"""
CareGrid AI — Medicine Redistribution Engine
===============================================
Identifies surplus/deficit facilities and generates
transfer recommendations to balance medicine stock.

Uses Haversine distance to minimize transfer costs.

Usage:
    from models.redistribution import RedistributionEngine
    engine = RedistributionEngine()
    transfers = engine.calculate_transfers()
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import func

from config.constants import MEDICINES
from models.database import get_db_session
from models.schema import Facility, StockItem
from utils.geo import haversine_distance

logger = logging.getLogger(__name__)


class RedistributionEngine:
    """
    Medicine redistribution engine.
    
    Matches surplus facilities (stock > 2x reorder) with
    deficit facilities (stock < reorder) to generate
    optimal transfer recommendations.
    """

    @staticmethod
    def find_surplus_facilities(medicine_name: str) -> list[dict]:
        """
        Find facilities with surplus stock for a given medicine.
        Surplus = current_stock > 2x reorder_level.

        Args:
            medicine_name: Name of the medicine.

        Returns:
            List of facility dicts with surplus info.
        """
        with get_db_session() as session:
            items = (
                session.query(StockItem, Facility)
                .join(Facility, StockItem.facility_id == Facility.id)
                .filter(
                    StockItem.medicine_name == medicine_name,
                    StockItem.current_stock > StockItem.reorder_level * 2,
                )
                .all()
            )

            return [
                {
                    "facility_id": facility.id,
                    "facility_name": facility.name,
                    "lat": facility.latitude,
                    "lon": facility.longitude,
                    "current_stock": item.current_stock,
                    "reorder_level": item.reorder_level,
                    "surplus": item.current_stock - item.reorder_level,
                    "transferable": item.current_stock - int(item.reorder_level * 1.5),
                }
                for item, facility in items
            ]

    @staticmethod
    def find_deficit_facilities(medicine_name: str) -> list[dict]:
        """
        Find facilities with deficit stock for a given medicine.
        Deficit = current_stock < reorder_level.

        Args:
            medicine_name: Name of the medicine.

        Returns:
            List of facility dicts with deficit info.
        """
        with get_db_session() as session:
            items = (
                session.query(StockItem, Facility)
                .join(Facility, StockItem.facility_id == Facility.id)
                .filter(
                    StockItem.medicine_name == medicine_name,
                    StockItem.current_stock < StockItem.reorder_level,
                )
                .all()
            )

            return [
                {
                    "facility_id": facility.id,
                    "facility_name": facility.name,
                    "lat": facility.latitude,
                    "lon": facility.longitude,
                    "current_stock": item.current_stock,
                    "reorder_level": item.reorder_level,
                    "deficit": item.reorder_level - item.current_stock,
                }
                for item, facility in items
            ]

    def _match_surplus_to_deficit(
        self,
        surplus_list: list[dict],
        deficit_list: list[dict],
        medicine_name: str,
    ) -> list[dict]:
        """
        Match surplus facilities to deficit facilities, minimizing distance.

        Args:
            surplus_list: List of surplus facility dicts.
            deficit_list: List of deficit facility dicts.
            medicine_name: Name of the medicine being transferred.

        Returns:
            List of transfer recommendation dicts.
        """
        transfers = []
        # Create mutable copies
        remaining_surplus = [dict(s) for s in surplus_list]
        remaining_deficit = [dict(d) for d in deficit_list]

        for deficit in remaining_deficit:
            if deficit["deficit"] <= 0:
                continue

            # Find nearest surplus facility with available stock
            best_source = None
            best_distance = float("inf")

            for surplus in remaining_surplus:
                if surplus["transferable"] <= 0:
                    continue

                dist = haversine_distance(
                    surplus["lat"], surplus["lon"],
                    deficit["lat"], deficit["lon"],
                )
                if dist < best_distance:
                    best_distance = dist
                    best_source = surplus

            if best_source is None:
                continue

            # Calculate transfer quantity
            transfer_qty = min(best_source["transferable"], deficit["deficit"])
            if transfer_qty <= 0:
                continue

            # Confidence based on distance (closer = higher confidence)
            if best_distance < 10:
                confidence = 95
            elif best_distance < 25:
                confidence = 85
            elif best_distance < 50:
                confidence = 70
            else:
                confidence = 55

            transfers.append({
                "source_facility": best_source["facility_name"],
                "source_facility_id": best_source["facility_id"],
                "destination_facility": deficit["facility_name"],
                "destination_facility_id": deficit["facility_id"],
                "medicine": medicine_name,
                "transfer_quantity": transfer_qty,
                "distance_km": round(best_distance, 1),
                "source_stock_after": best_source["current_stock"] - transfer_qty,
                "dest_stock_after": deficit["current_stock"] + transfer_qty,
                "reason": (
                    f"{deficit['facility_name']} has {deficit['current_stock']} units "
                    f"(needs {deficit['reorder_level']}). "
                    f"{best_source['facility_name']} has surplus of "
                    f"{best_source['surplus']} units."
                ),
                "confidence": confidence,
                "suggested_action": (
                    f"Transfer {transfer_qty} units of {medicine_name} from "
                    f"{best_source['facility_name']} to {deficit['facility_name']} "
                    f"({best_distance:.1f} km distance)"
                ),
            })

            # Update remaining quantities
            best_source["transferable"] -= transfer_qty
            deficit["deficit"] -= transfer_qty

        return transfers

    def calculate_transfers(self, medicine_name: Optional[str] = None) -> list[dict]:
        """
        Calculate all recommended transfers across all medicines or a specific one.

        Args:
            medicine_name: Optional specific medicine. If None, checks all medicines.

        Returns:
            List of transfer recommendation dicts sorted by priority.
        """
        all_transfers = []

        medicines_to_check = (
            [medicine_name] if medicine_name
            else [m["name"] for m in MEDICINES]
        )

        for med_name in medicines_to_check:
            try:
                surplus = self.find_surplus_facilities(med_name)
                deficit = self.find_deficit_facilities(med_name)

                if surplus and deficit:
                    transfers = self._match_surplus_to_deficit(
                        surplus, deficit, med_name
                    )
                    all_transfers.extend(transfers)
            except Exception as e:
                logger.error(
                    "Error calculating transfers for %s: %s", med_name, e
                )

        # Sort by distance (prioritize shorter transfers)
        all_transfers.sort(key=lambda x: x["distance_km"])

        return all_transfers
