"""Public GIS types for find_routes and get_segments."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


VEHICLE_TYPES = ("truck", "van", "car")

# Typical free-flow speeds by road class. Used only for duration estimates.
SPEED_KMH = {
    "car": {"major": 70.0, "collector": 50.0, "local": 35.0, "special": 40.0, "unknown": 30.0},
    "van": {"major": 60.0, "collector": 45.0, "local": 30.0, "special": 35.0, "unknown": 25.0},
    "truck": {"major": 50.0, "collector": 35.0, "local": 25.0, "special": 30.0, "unknown": 20.0},
}


@dataclass(frozen=True)
class Point:
    lat: float
    lng: float

    def as_dict(self) -> dict:
        return {"lat": self.lat, "lng": self.lng}


@dataclass
class SegmentRecord:
    segment_id: str
    length_km: float
    road_class: str
    road_type: str
    slope_deg: float | None
    is_oneway: bool
    coordinates: list[list[float]]
    surface: str | None = None

    def as_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "length_km": round(self.length_km, 6),
            "road_class": self.road_class,
            "road_type": self.road_type,
            "slope_deg": self.slope_deg,
            "is_oneway": self.is_oneway,
            "coordinates": self.coordinates,
            "surface": self.surface,
        }


@dataclass
class RouteCandidate:
    route_id: str
    distance_km: float
    duration_min: float
    geometry: dict
    segment_ids: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        payload = asdict(self)
        payload["distance_km"] = round(self.distance_km, 3)
        payload["duration_min"] = round(self.duration_min, 1)
        return payload
