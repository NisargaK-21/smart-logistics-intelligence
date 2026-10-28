from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.schemas.meta import CoverageResponse

router = APIRouter()


@router.get(
    "/coverage",
    response_model=CoverageResponse,
    summary="Study-area bounding box and supported vehicle types",
)
def get_coverage():
    return CoverageResponse(
        bbox=settings.STUDY_AREA_BBOX,
        vehicle_types=settings.SUPPORTED_VEHICLE_TYPES,
    )
