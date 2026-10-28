"""GIS module errors. Backend maps these to the API error codes."""


class GisError(Exception):
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidRequestError(GisError):
    code = "INVALID_REQUEST"


class OutOfCoverageError(GisError):
    code = "OUT_OF_COVERAGE"


class NoRouteFoundError(GisError):
    code = "NO_ROUTE_FOUND"
