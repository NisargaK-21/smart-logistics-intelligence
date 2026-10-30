"""Backend adapter for Person 1's public :mod:`routing` interface."""

from __future__ import annotations

from typing import Any

from backend.app.core.config import settings
from backend.app.core.errors import (
    DependencyUnavailableException,
    InvalidRequestException,
    NoRouteFoundException,
    OutOfCoverageException,
)
from routing import (
    GisError,
    InvalidRequestError,
    NoRouteFoundError,
    OutOfCoverageError,
    get_coverage,
    get_segments,
    find_routes,
)


class GISService:
    """Translate routing's public API and domain errors for the HTTP layer."""

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
        self, origin: dict[str, float], destination: dict[str, float], vehicle_type: str
    ) -> list[dict[str, Any]]:
        self._ensure_available()
        try:
            return [self._as_dict(route) for route in find_routes(origin, destination, vehicle_type)]
        except GisError as error:
            self._raise_mapped(error)

    def get_segments(self, segment_ids: list[str]) -> dict[str, dict[str, Any]]:
        self._ensure_available()
        try:
            records = get_segments(segment_ids)
        except GisError as error:
            self._raise_mapped(error)
        return {record.segment_id: self._as_dict(record) for record in records}

    def get_coverage(self) -> dict[str, Any]:
        self._ensure_available()
        try:
            return get_coverage()
        except Exception as error:
            raise DependencyUnavailableException(
                module="gis", message="GIS coverage metadata is unavailable."
            ) from error


gis_service = GISService()
