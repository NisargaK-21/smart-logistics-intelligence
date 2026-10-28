from fastapi import APIRouter
from backend.app.schemas.route_plan import RoutePlanRequest, RoutePlanResponse
from backend.app.services.orchestrator import orchestrator

router = APIRouter()


@router.post(
    "/plan",
    response_model=RoutePlanResponse,
    summary="Plan candidate routes with multi-segment risk scoring and recommendation",
)
def plan_routes(request: RoutePlanRequest):
    return orchestrator.plan_routes(request)
