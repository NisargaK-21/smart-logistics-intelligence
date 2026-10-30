from fastapi import APIRouter
from backend.app.schemas.common import ErrorResponse
from backend.app.schemas.route_plan import RoutePlanRequest, RoutePlanResponse
from backend.app.services.orchestrator import orchestrator

router = APIRouter()


@router.post(
    "/plan",
    response_model=RoutePlanResponse,
    summary="Plan candidate routes with multi-segment risk scoring and recommendation",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "No connected route found"},
        422: {"model": ErrorResponse, "description": "Coordinates are outside study-area coverage"},
        503: {"model": ErrorResponse, "description": "A required dependency is unavailable"},
        500: {"model": ErrorResponse, "description": "Unexpected server error"},
    },
)
def plan_routes(request: RoutePlanRequest):
    return orchestrator.plan_routes(request)
