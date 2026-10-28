"""GIS & routing module (Person 1).

Public functions for the backend:

    find_routes(origin, destination, vehicle_type)
    get_segments(segment_ids)
    get_coverage()
"""

from routing.exceptions import (
    GisError,
    InvalidRequestError,
    NoRouteFoundError,
    OutOfCoverageError,
)
from routing.models import VEHICLE_TYPES, Point, RouteCandidate, SegmentRecord
from routing.service import GisService, find_routes, get_coverage, get_segments, get_service

__all__ = [
    "GisError",
    "GisService",
    "InvalidRequestError",
    "NoRouteFoundError",
    "OutOfCoverageError",
    "Point",
    "RouteCandidate",
    "SegmentRecord",
    "VEHICLE_TYPES",
    "find_routes",
    "get_coverage",
    "get_segments",
    "get_service",
]
