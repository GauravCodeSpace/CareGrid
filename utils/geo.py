"""
CareGrid AI — Geospatial Utilities
=====================================
Provides distance calculations, nearest-facility lookup, and map centering.
Uses the Haversine formula for great-circle distance on a sphere.

Usage:
    from utils.geo import haversine_distance, find_nearest_facility, get_map_center
"""

from __future__ import annotations

import math
from typing import Optional


# Earth's mean radius in kilometres (WGS-84)
_EARTH_RADIUS_KM: float = 6_371.0


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate the great-circle distance between two points on Earth.

    Uses the Haversine formula which gives distances accurate to a few
    metres for typical healthcare-district scales (< 100 km).

    Args:
        lat1: Latitude of point 1 in decimal degrees.
        lon1: Longitude of point 1 in decimal degrees.
        lat2: Latitude of point 2 in decimal degrees.
        lon2: Longitude of point 2 in decimal degrees.

    Returns:
        Distance in kilometres.
    """
    # Convert decimal degrees to radians
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)

    a = (
        math.sin(Δφ / 2) ** 2
        + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return _EARTH_RADIUS_KM * c


def find_nearest_facility(
    lat: float,
    lon: float,
    facilities: list[dict],
) -> Optional[dict]:
    """
    Find the facility closest to the given coordinates.

    Each facility dict must contain at minimum ``lat`` (or ``latitude``)
    and ``lon`` (or ``longitude``) keys.

    Args:
        lat: Reference latitude.
        lon: Reference longitude.
        facilities: List of facility dicts, each with lat/lon keys.

    Returns:
        The nearest facility dict with an added ``distance_km`` key,
        or ``None`` if the list is empty.
    """
    if not facilities:
        return None

    best: Optional[dict] = None
    best_dist: float = float("inf")

    for fac in facilities:
        fac_lat = fac.get("lat") or fac.get("latitude", 0.0)
        fac_lon = fac.get("lon") or fac.get("longitude", 0.0)
        dist = haversine_distance(lat, lon, fac_lat, fac_lon)
        if dist < best_dist:
            best_dist = dist
            best = fac

    if best is not None:
        result = dict(best)
        result["distance_km"] = round(best_dist, 2)
        return result
    return None


def get_map_center(facilities: list[dict]) -> tuple[float, float]:
    """
    Compute the geographic centroid of a list of facilities.

    Useful for setting the initial view of a Folium / Google Maps widget.

    Args:
        facilities: List of facility dicts, each with lat/lon keys.

    Returns:
        Tuple of (latitude, longitude) representing the centroid.
        Falls back to Lucknow centre (26.85, 80.95) if the list is empty.
    """
    if not facilities:
        # Default: approximate centre of Lucknow district
        return (26.85, 80.95)

    total_lat: float = 0.0
    total_lon: float = 0.0
    count: int = 0

    for fac in facilities:
        fac_lat = fac.get("lat") or fac.get("latitude")
        fac_lon = fac.get("lon") or fac.get("longitude")
        if fac_lat is not None and fac_lon is not None:
            total_lat += float(fac_lat)
            total_lon += float(fac_lon)
            count += 1

    if count == 0:
        return (26.85, 80.95)

    return (round(total_lat / count, 4), round(total_lon / count, 4))
