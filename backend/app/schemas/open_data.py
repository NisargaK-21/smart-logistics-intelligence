from pydantic import BaseModel


class PlaceResult(BaseModel):
    display_name: str
    lat: float
    lng: float


class CurrentWeather(BaseModel):
    latitude: float
    longitude: float
    elevation_m: float | None
    time: str
    temperature_c: float
    precipitation_mm: float
    rain_mm: float
    weather_code: int
    wind_speed_kmh: float
    wind_gusts_kmh: float
    updated_at: str
    source: str
