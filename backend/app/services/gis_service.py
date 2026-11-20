"""Backend adapter for Person 1's public :mod:`routing` interface."""

from __future__ import annotations

import json
import math
import threading
from collections import OrderedDict
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from backend.app.core.config import settings
from backend.app.core.errors import (
    DependencyUnavailableException,
    InvalidRequestException,
    NoRouteFoundException,
    OutOfCoverageException,
)
from backend.app.services.terrain_service import terrain_service
from routing.geo import (
    point_in_bbox,
    point_to_linestring_distance_km,
    validate_lat_lng,
)
from routing import (
    GisError,
    InvalidRequestError,
    NoRouteFoundError,
    OutOfCoverageError,
    get_coverage,
    get_service,
    get_segments,
    find_routes,
)
from routing.models import VEHICLE_TYPES

NORTHEAST_BBOX = [87.5, 21.5, 97.8, 29.9]
MAX_INCIDENT_MATCH_DISTANCE_KM = 0.5


class GISService:
    """Translate routing's public API and domain errors for the HTTP layer."""

    def __init__(self, graph=None, router_url: str | None = None):
        configured_url = settings.OSRM_ROUTER_URL if router_url is None else router_url
        self.router_url = configured_url.rstrip("/")
        self.graph = graph if graph is not None else (None if self.router_url else get_service().graph)
        self._use_osrm = graph is None and bool(self.router_url)
        self._route_segments: OrderedDict[str, dict[str, dict[str, Any]]] = OrderedDict()
        self._cache_lock = threading.Lock()

    def check_health(self) -> str:
        return "ok" if settings.GIS_SERVICE_ENABLED else "down"

    def _ensure_available(self) -> None:
        if self.check_health() != "ok":
            raise DependencyUnavailableException(module="gis")

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return value.as_dict() if hasattr(value, "as_dict") else dict(value)

    @staticmethod
    def _raise_mapped(error: Exception) -> None:
        details = getattr(error, "details", None)
        if isinstance(error, InvalidRequestError):
            raise InvalidRequestException(str(error), details) from error
        if isinstance(error, OutOfCoverageError):
            normalized = dict(details or {})
            if "field" in normalized:
                normalized.setdefault("point", normalized.pop("field"))
            if "bbox" in normalized:
                normalized.setdefault("coverage_bbox", normalized.pop("bbox"))
            raise OutOfCoverageException(str(error), normalized) from error
        if isinstance(error, NoRouteFoundError):
            normalized = dict(details or {})
            normalized.setdefault("origin_snapped", True)
            normalized.setdefault("destination_snapped", True)
            raise NoRouteFoundException(str(error), normalized) from error
        if isinstance(error, GisError):
            raise DependencyUnavailableException(
                module="gis", message=str(error), details=details
            ) from error
        raise error

    def find_routes(
        self,
        origin: dict[str, float],
        destination: dict[str, float],
        vehicle_type: str,
        blocked_segment_ids: set[str] | None = None,
        blocked_points: list[tuple[float, float]] | None = None,
    ) -> list[dict[str, Any]]:
        self._ensure_available()
        if self._use_osrm:
            routes = self._find_osrm_routes(origin, destination, vehicle_type)
            if not blocked_points:
                return routes
            return [
                route
                for route in routes
                if not self._route_intersects_blocked_points(
                    route["segment_ids"], blocked_points
                )
            ]
        try:
            return [
                self._as_dict(route)
                for route in find_routes(
                    origin,
                    destination,
                    vehicle_type,
                    blocked_segment_ids=blocked_segment_ids,
                )
            ]
        except GisError as error:
            self._raise_mapped(error)

    def nearest_segment(self, lng: float, lat: float) -> tuple[str | None, float]:
        if self.graph is None:
            return None, float("inf")
        return self.graph.nearest_segment(lng, lat)

    def _route_intersects_blocked_points(
        self, segment_ids: list[str], blocked_points: list[tuple[float, float]]
    ) -> bool:
        segments = self.get_segments(segment_ids)
        return any(
            point_to_linestring_distance_km(lng, lat, segment["coordinates"])
            <= MAX_INCIDENT_MATCH_DISTANCE_KM
            for lng, lat in blocked_points
            for segment in segments.values()
        )

    @staticmethod
    def _validate_osrm_point(point: dict[str, float], label: str) -> None:
        try:
            lat = float(point["lat"])
            lng = float(point["lng"])
            validate_lat_lng(lat, lng)
        except (KeyError, TypeError, ValueError) as error:
            raise InvalidRequestException(
                f"{label} must contain valid latitude and longitude.",
                {"field": label},
            ) from error
        if not point_in_bbox(lng, lat, NORTHEAST_BBOX):
            raise OutOfCoverageException(
                f"{label} is outside Northeast India coverage.",
                {"point": label, "coverage_bbox": NORTHEAST_BBOX},
            )

    def _request_osrm(self, origin: dict[str, float], destination: dict[str, float]) -> dict:
        coordinates = (
            f"{origin['lng']},{origin['lat']};"
            f"{destination['lng']},{destination['lat']}"
        )
        query = urlencode({
            "alternatives": "3",
            "steps": "true",
            "overview": "full",
            "geometries": "geojson",
        })
        request = Request(
            f"{self.router_url}/route/v1/driving/{coordinates}?{query}",
            headers={"Accept": "application/json", "User-Agent": "NER-ResQ/1.0"},
        )
        try:
            with urlopen(request, timeout=15) as response:
                return json.loads(response.read())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise DependencyUnavailableException(
                module="gis",
                message="OpenStreetMap routing could not be reached.",
            ) from error

    def _find_osrm_routes(
        self, origin: dict[str, float], destination: dict[str, float], vehicle_type: str
    ) -> list[dict[str, Any]]:
        self._validate_osrm_point(origin, "origin")
        self._validate_osrm_point(destination, "destination")
        if vehicle_type not in VEHICLE_TYPES:
            raise InvalidRequestException(
                "vehicle_type must be truck, van or car.",
                {"vehicle_type": vehicle_type},
            )
        if origin["lat"] == destination["lat"] and origin["lng"] == destination["lng"]:
            raise InvalidRequestException(
                "origin and destination must differ.",
                {"field": "destination"},
            )

        payload = self._request_osrm(origin, destination)
        if payload.get("code") != "Ok" or not payload.get("routes"):
            raise NoRouteFoundException(
                "No drivable OpenStreetMap route connects these places.",
                {"origin_snapped": False, "destination_snapped": False},
            )

        candidates: list[dict[str, Any]] = []
        for route_index, route in enumerate(payload["routes"]):
            route_id = f"osrm-{uuid4().hex[:12]}-{route_index + 1}"
            route_segments: dict[str, dict[str, Any]] = {}
            segment_ids: list[str] = []
            for leg in route.get("legs", []):
                for step in leg.get("steps", []):
                    coordinates = (
                        step.get("geometry", {}).get("coordinates", [])
                        if isinstance(step.get("geometry"), dict)
                        else []
                    )
                    distance_m = float(step.get("distance", 0.0))
                    if len(coordinates) < 2 or not math.isfinite(distance_m) or distance_m <= 0:
                        continue
                    segment_id = f"{route_id}:step-{len(segment_ids) + 1}"
                    segment_ids.append(segment_id)
                    terrain_attrs = terrain_service.query_linestring(coordinates)
                    route_segments[segment_id] = {
                        "segment_id": segment_id,
                        "length_km": distance_m / 1000.0,
                        "road_class": "unknown",
                        "road_type": "unknown",
                        "slope_deg": terrain_attrs.get("slope_deg"),
                        "elevation_m": terrain_attrs.get("elevation_m"),
                        "ruggedness": terrain_attrs.get("ruggedness"),
                        "is_oneway": False,
                        "coordinates": coordinates,
                        "surface": None,
                    }

            geometry = route.get("geometry") or {}
            if geometry.get("type") != "LineString" or len(geometry.get("coordinates", [])) < 2:
                raise DependencyUnavailableException(
                    module="gis",
                    message="OpenStreetMap routing returned invalid route geometry.",
                )
            if not segment_ids:
                segment_id = f"{route_id}:step-1"
                segment_ids.append(segment_id)
                terrain_attrs = terrain_service.query_linestring(geometry["coordinates"])
                route_segments[segment_id] = {
                    "segment_id": segment_id,
                    "length_km": float(route.get("distance", 0.0)) / 1000.0,
                    "road_class": "unknown",
                    "road_type": "unknown",
                    "slope_deg": terrain_attrs.get("slope_deg"),
                    "elevation_m": terrain_attrs.get("elevation_m"),
                    "ruggedness": terrain_attrs.get("ruggedness"),
                    "is_oneway": False,
                    "coordinates": geometry["coordinates"],
                    "surface": None,
                }

            candidates.append({
                "route_id": route_id,
                "distance_km": float(route.get("distance", 0.0)) / 1000.0,
                "duration_min": float(route.get("duration", 0.0)) / 60.0,
                "geometry": geometry,
                "segment_ids": segment_ids,
            })
            with self._cache_lock:
                self._route_segments[route_id] = route_segments
                self._route_segments.move_to_end(route_id)
                while len(self._route_segments) > 30:
                    self._route_segments.popitem(last=False)

        return candidates

    def get_segments(self, segment_ids: list[str]) -> dict[str, dict[str, Any]]:
        if self._use_osrm:
            records: dict[str, dict[str, Any]] = {}
            with self._cache_lock:
                for segment_id in segment_ids:
                    route_id = segment_id.rsplit(":step-", 1)[0]
                    route_segments = self._route_segments.get(route_id)
                    if route_segments and segment_id in route_segments:
                        records[segment_id] = route_segments[segment_id]
            missing = [segment_id for segment_id in segment_ids if segment_id not in records]
            if missing:
                raise InvalidRequestException(
                    "One or more route segments have expired.",
                    {"missing": missing},
                )
            return records
        self._ensure_available()
        try:
            records = get_segments(segment_ids)
        except GisError as error:
            self._raise_mapped(error)
        results: dict[str, dict[str, Any]] = {}
        for record in records:
            rec_dict = self._as_dict(record)
            coords = rec_dict.get("coordinates", [])
            if coords:
                terrain_attrs = terrain_service.query_linestring(coords)
                if terrain_attrs.get("terrain_available"):
                    rec_dict["slope_deg"] = terrain_attrs.get("slope_deg")
                    rec_dict["elevation_m"] = terrain_attrs.get("elevation_m")
                    rec_dict["ruggedness"] = terrain_attrs.get("ruggedness")
                elif getattr(settings, "TERRAIN_ENABLED", True):
                    rec_dict["slope_deg"] = None
                    rec_dict["elevation_m"] = None
                    rec_dict["ruggedness"] = None
            results[record.segment_id] = rec_dict
        return results

    def get_coverage(self) -> dict[str, Any]:
        if self._use_osrm:
            return {
                "bbox": NORTHEAST_BBOX,
                "vehicle_types": list(VEHICLE_TYPES),
            }
        self._ensure_available()
        try:
            return get_coverage()
        except Exception as error:
            raise DependencyUnavailableException(
                module="gis", message="GIS coverage metadata is unavailable."
            ) from error


gis_service = GISService()
