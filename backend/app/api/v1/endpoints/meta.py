from fastapi import APIRouter
from backend.app.schemas.common import ErrorResponse
from backend.app.services.gis_service import gis_service
from backend.app.schemas.meta import CoverageResponse

router = APIRouter()


@router.get(
    "/coverage",
    response_model=CoverageResponse,
    summary="Study-area bounding box and supported vehicle types",
    responses={
        503: {"model": ErrorResponse, "description": "GIS dependency is unavailable"},
        500: {"model": ErrorResponse, "description": "Unexpected server error"},
    },
)
def get_coverage():
    coverage = gis_service.get_coverage()
    return CoverageResponse(
        bbox=coverage["bbox"],
        vehicle_types=coverage["vehicle_types"],
    )
