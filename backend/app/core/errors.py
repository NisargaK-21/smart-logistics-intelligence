from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


# Error code constants
INVALID_REQUEST = "INVALID_REQUEST"
NO_ROUTE_FOUND = "NO_ROUTE_FOUND"
OUT_OF_COVERAGE = "OUT_OF_COVERAGE"
DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
INTERNAL_ERROR = "INTERNAL_ERROR"


class AppException(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class InvalidRequestException(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=INVALID_REQUEST,
            message=message,
            details=details,
        )


class NoRouteFoundException(AppException):
    def __init__(
        self,
        message: str = "No connected road path between the two points.",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code=NO_ROUTE_FOUND,
            message=message,
            details=details or {"origin_snapped": True, "destination_snapped": True},
        )


class OutOfCoverageException(AppException):
    def __init__(
        self,
        message: str = "Coordinates are outside the supported study-area coverage bounding box.",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=422,
            code=OUT_OF_COVERAGE,
            message=message,
            details=details,
        )


class DependencyUnavailableException(AppException):
    def __init__(
        self,
        module: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        det = details or {}
        det["module"] = module
        msg = message or f"Core dependency '{module}' is down or unreachable."
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=DEPENDENCY_UNAVAILABLE,
            message=msg,
            details=det,
        )


def build_error_response(status_code: int, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return build_error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Format validation errors into clear field details
        details: Dict[str, Any] = {}
        error_msgs = []
        for err in exc.errors():
            loc = ".".join(str(l) for l in err.get("loc", []) if l != "body")
            msg = err.get("msg", "Invalid value").removeprefix("Value error, ")
            if loc:
                details[loc] = msg
                error_msgs.append(f"{loc}: {msg}")
            else:
                if msg == "Destination must differ from origin":
                    details["field"] = "destination"
                elif msg == "departure_time must include an ISO 8601 UTC offset":
                    details["field"] = "departure_time"
                else:
                    details["field"] = "request"
                error_msgs.append(msg)

        summary_message = "; ".join(error_msgs) if error_msgs else "Validation error on request payload"
        return build_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=INVALID_REQUEST,
            message=summary_message,
            details=details,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        code_map = {
            400: INVALID_REQUEST,
            404: NO_ROUTE_FOUND,
            422: OUT_OF_COVERAGE,
            503: DEPENDENCY_UNAVAILABLE,
        }
        code = code_map.get(exc.status_code, INTERNAL_ERROR)
        return build_error_response(
            status_code=exc.status_code,
            code=code,
            message=str(exc.detail),
            details={},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        return build_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code=INTERNAL_ERROR,
            message="An unexpected internal server error occurred.",
            details={"error_type": exc.__class__.__name__},
        )
