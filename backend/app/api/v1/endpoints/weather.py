from fastapi import APIRouter, Query
from backend.app.core.config import settings
from backend.app.core.errors import DependencyUnavailableException
from backend.app.schemas.common import ErrorResponse
from backend.app.schemas.open_data import CurrentWeather
from backend.app.services.open_data_service import open_data_service

router = APIRouter()


@router.get(
    "/current",
    response_model=CurrentWeather,
    summary="Get current modelled weather conditions",
    responses={503: {"model": ErrorResponse, "description": "Weather provider is unavailable"}},
)
def get_current_weather(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
):
    if not settings.WEATHER_AVAILABLE:
        raise DependencyUnavailableException(
            module="weather",
            message="Current weather is disabled by the service configuration.",
        )
    return open_data_service.get_current_weather(lat, lng)
