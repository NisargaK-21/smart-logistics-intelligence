"""Person 1 public GIS interface used by the backend."""

from __future__ import annotations

from routing.exceptions import InvalidRequestError, NoRouteFoundError, OutOfCoverageError
from routing.geo import point_in_bbox, validate_lat_lng
from routing.graph import RoadGraph, vehicle_type_ok
from routing.loader import load_graph
from routing.models import VEHICLE_TYPES, Point, RouteCandidate, SegmentRecord
from routing.pathfinder import find_k_paths

# Snap farther than this and the query is treated as unreachable, not covered.
MAX_SNAP_KM = 2.5


class GisService:
    def __init__(self, graph: RoadGraph | None = None, max_snap_km: float = MAX_SNAP_KM):
        self.graph = graph if graph is not None else load_graph()
        self.max_snap_km = max_snap_km

    def _point(self, value: dict | Point, label: str) -> Point:
        if isinstance(value, Point):
            lat, lng = value.lat, value.lng
        elif isinstance(value, dict):
            if "lat" not in value or "lng" not in value:
                raise InvalidRequestError(
                    f"{label} must include lat and lng.",
                    {"field": label},
                )
            lat, lng = value["lat"], value["lng"]
        else:
            raise InvalidRequestError(f"{label} must be an object with lat and lng.")

        try:
            lat_f = float(lat)
            lng_f = float(lng)
            validate_lat_lng(lat_f, lng_f)
        except (TypeError, ValueError) as exc:
            raise InvalidRequestError(str(exc), {"field": label}) from exc
        return Point(lat=lat_f, lng=lng_f)

    def _snap(self, point: Point, label: str) -> str:
        if not point_in_bbox(point.lng, point.lat, self.graph.bbox):
            raise OutOfCoverageError(
                f"{label} is outside the study area.",
                {"field": label, "bbox": self.graph.bbox},
            )
        node, distance_km = self.graph.snap(point.lng, point.lat)
        if not node or distance_km > self.max_snap_km:
            raise NoRouteFoundError(
                f"{label} could not be snapped to the road network.",
                {"field": label, "snap_distance_km": round(distance_km, 3)},
            )
        return node

    def find_routes(
        self,
        origin: dict | Point,
        destination: dict | Point,
        vehicle_type: str,
        max_routes: int = 3,
    ) -> list[RouteCandidate]:
        origin_pt = self._point(origin, "origin")
        dest_pt = self._point(destination, "destination")
        if vehicle_type not in VEHICLE_TYPES or not vehicle_type_ok(vehicle_type):
            raise InvalidRequestError(
                "vehicle_type must be truck, van or car.",
                {"vehicle_type": vehicle_type},
            )
        if origin_pt.lat == dest_pt.lat and origin_pt.lng == dest_pt.lng:
            raise InvalidRequestError(
                "origin and destination must differ.",
                {"origin": origin_pt.as_dict(), "destination": dest_pt.as_dict()},
            )

        start = self._snap(origin_pt, "origin")
        end = self._snap(dest_pt, "destination")
        if start == end:
            raise InvalidRequestError(
                "origin and destination snap to the same road node.",
                {"origin": origin_pt.as_dict(), "destination": dest_pt.as_dict()},
            )

        routes = find_k_paths(self.graph, start, end, vehicle_type, max_routes=max_routes)
        if not routes:
            raise NoRouteFoundError(
                "Points snapped but no connected path exists.",
                {"origin": origin_pt.as_dict(), "destination": dest_pt.as_dict()},
            )
        return routes

    def get_segments(self, segment_ids: list[str]) -> list[SegmentRecord]:
        if not isinstance(segment_ids, list):
            raise InvalidRequestError("segment_ids must be a list.")
        missing = [sid for sid in segment_ids if sid not in self.graph.segments]
        if missing:
            raise InvalidRequestError(
                "One or more segment ids are unknown.",
                {"missing": missing},
            )
        return [self.graph.segments[sid] for sid in segment_ids]

    def get_coverage(self) -> dict:
        return {
            "bbox": self.graph.bbox,
            "vehicle_types": list(VEHICLE_TYPES),
            "segment_count": len(self.graph.segments),
            "node_count": len(self.graph.nodes),
        }


_default_service: GisService | None = None


def get_service() -> GisService:
    global _default_service
    if _default_service is None:
        _default_service = GisService()
    return _default_service


def find_routes(origin, destination, vehicle_type: str, max_routes: int = 3):
    return get_service().find_routes(origin, destination, vehicle_type, max_routes=max_routes)


def get_segments(segment_ids: list[str]):
    return get_service().get_segments(segment_ids)


def get_coverage() -> dict:
    return get_service().get_coverage()
