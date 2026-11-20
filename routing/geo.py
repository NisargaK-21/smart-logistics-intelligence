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


def point_to_linestring_distance_km(
    lng: float, lat: float, coords: list[list[float]]
) -> float:
    """Return the closest local-projection distance from a point to a line."""
    if not math.isfinite(lng) or not math.isfinite(lat) or not coords:
        return float("inf")

    km_per_degree = EARTH_RADIUS_KM * math.pi / 180.0
    longitude_scale = km_per_degree * max(abs(math.cos(math.radians(lat))), 1e-6)
    points: list[tuple[float, float]] = []
    for coordinate in coords:
        try:
            point_lng = float(coordinate[0])
            point_lat = float(coordinate[1])
        except (IndexError, TypeError, ValueError):
            continue
        if math.isfinite(point_lng) and math.isfinite(point_lat):
            points.append((point_lng, point_lat))

    if not points:
        return float("inf")
    if len(points) == 1:
        point_lng, point_lat = points[0]
        return haversine_km(lng, lat, point_lng, point_lat)

    best_distance = float("inf")
    for (lng1, lat1), (lng2, lat2) in zip(points, points[1:]):
        x1 = (lng1 - lng) * longitude_scale
        y1 = (lat1 - lat) * km_per_degree
        x2 = (lng2 - lng) * longitude_scale
        y2 = (lat2 - lat) * km_per_degree
        dx = x2 - x1
        dy = y2 - y1
        length_squared = dx * dx + dy * dy
        fraction = (
            0.0
            if length_squared == 0
            else min(max(-(x1 * dx + y1 * dy) / length_squared, 0.0), 1.0)
        )
        distance = math.hypot(x1 + fraction * dx, y1 + fraction * dy)
        best_distance = min(best_distance, distance)
    return best_distance


def point_in_bbox(lng: float, lat: float, bbox: list[float]) -> bool:
    min_lng, min_lat, max_lng, max_lat = bbox
    return min_lng <= lng <= max_lng and min_lat <= lat <= max_lat
