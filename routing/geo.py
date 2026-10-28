"""Coordinate helpers. All geography is WGS84; GeoJSON order is [lng, lat]."""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0
NODE_PRECISION = 6


def validate_lat_lng(lat: float, lng: float) -> None:
    if not math.isfinite(lat) or not math.isfinite(lng):
        raise ValueError("Coordinates must be finite numbers.")
    if lat < -90 or lat > 90:
        raise ValueError("lat must be between -90 and 90.")
    if lng < -180 or lng > 180:
        raise ValueError("lng must be between -180 and 180.")


def node_key(lng: float, lat: float) -> tuple[float, float]:
    return (round(float(lng), NODE_PRECISION), round(float(lat), NODE_PRECISION))


def node_id(lng: float, lat: float) -> str:
    key = node_key(lng, lat)
    return f"{key[0]:.{NODE_PRECISION}f},{key[1]:.{NODE_PRECISION}f}"


def haversine_km(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def linestring_length_km(coords: list[list[float]]) -> float:
    total = 0.0
    for (lng1, lat1), (lng2, lat2) in zip(coords, coords[1:]):
        total += haversine_km(lng1, lat1, lng2, lat2)
    return total


def point_in_bbox(lng: float, lat: float, bbox: list[float]) -> bool:
    min_lng, min_lat, max_lng, max_lat = bbox
    return min_lng <= lng <= max_lng and min_lat <= lat <= max_lat
