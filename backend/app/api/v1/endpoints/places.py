from fastapi import APIRouter, Query
from backend.app.schemas.common import ErrorResponse
from backend.app.schemas.open_data import PlaceResult
from backend.app.services.open_data_service import open_data_service

router = APIRouter()


@router.get(
    "/search",
    response_model=list[PlaceResult],
    summary="Search Northeast India places using OpenStreetMap",
    responses={503: {"model": ErrorResponse, "description": "Place search provider is unavailable"}},
)
def search_places(q: str = Query(..., min_length=3, max_length=150)):
    return open_data_service.search_places(q)
