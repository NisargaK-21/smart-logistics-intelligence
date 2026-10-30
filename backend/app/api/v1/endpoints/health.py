from fastapi import APIRouter
from backend.app.core.errors import DependencyUnavailableException
from backend.app.schemas.common import ErrorResponse
from backend.app.schemas.health import HealthResponse, ModuleStatus
from backend.app.services.gis_service import gis_service
from backend.app.services.risk_service import risk_service

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Status of backend orchestrator, GIS module, and risk module",
    responses={
        503: {"model": ErrorResponse, "description": "A required dependency is unavailable"},
        500: {"model": ErrorResponse, "description": "Unexpected server error"},
    },
)
def get_health():
    gis_status = gis_service.check_health()
    risk_status, weather_status = risk_service.check_health()

    # In accordance with the contract:
    # "Returns 200 with {"status": "ok", "modules": {"gis": "ok", "risk": "ok", "weather": "degraded"}}.
    #  Returns 503 if GIS or risk is down. The frontend calls it on load to show a status badge."
    if gis_status != "ok":
        raise DependencyUnavailableException(
            module="gis",
            message="Core dependency 'gis' is unavailable or unhealthy."
        )

    if risk_status != "ok":
        raise DependencyUnavailableException(
            module="risk",
            message="Core dependency 'risk' is unavailable or unhealthy."
        )

    return HealthResponse(
        status="ok",
        modules=ModuleStatus(
            gis=gis_status,
            risk=risk_status,
            weather=weather_status,
        ),
    )
