from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator
from backend.app.schemas.common import Coordinates


class RoutePlanRequest(BaseModel):
    origin: Coordinates
    destination: Coordinates
    vehicle_type: Literal["truck", "van", "car"] = Field(..., description="Vehicle type: truck, van, or car")
    commodity_type: Optional[str] = Field(default=None, description="Cargo/Commodity type: e.g. Medicine, Food Supplies, Fuel, Emergency Kits")
    departure_time: Optional[datetime] = Field(default=None, description="ISO 8601 departure timestamp with offset")

    @model_validator(mode="after")
    def check_origin_destination_different(self) -> "RoutePlanRequest":
        if self.origin.lat == self.destination.lat and self.origin.lng == self.destination.lng:
            raise ValueError("Destination must differ from origin")
        if self.departure_time is not None and self.departure_time.tzinfo is None:
            raise ValueError("departure_time must include an ISO 8601 UTC offset")
        return self


class GeoJSONGeometry(BaseModel):
    type: str = Field(default="LineString", description="GeoJSON geometry type")
    coordinates: List[List[float]] = Field(..., description="Array of [lng, lat] coordinate pairs")


class SegmentWeatherForecast(BaseModel):
    estimated_arrival_time: str = Field(..., description="ISO 8601 estimated arrival time at segment start")
    forecast_time: str = Field(..., description="Corresponding forecast hour timestamp")
    temperature_c: float
    precipitation_mm: float
    rain_mm: float
    weather_code: int
    wind_speed_kmh: float
    wind_gusts_kmh: float


class SegmentRisk(BaseModel):
    segment_id: str
    risk_score: int = Field(..., ge=0, le=100)
    coordinates: List[List[float]] = Field(..., description="Segment coordinate pairs [[lng, lat], ...]")
    slope_deg: Optional[float] = Field(default=None, description="Average terrain slope in degrees")
    elevation_m: Optional[float] = Field(default=None, description="Average elevation in meters")
    ruggedness: Optional[float] = Field(default=None, description="Average terrain ruggedness index")
    weather_forecast: Optional[SegmentWeatherForecast] = Field(
        default=None, description="Time-of-arrival weather forecast for this segment"
    )


class RiskFactor(BaseModel):
    name: str
    contribution: float = Field(..., ge=0)
    detail: Optional[str] = None


class Route(BaseModel):
    route_id: str
    distance_km: float
    estimated_duration_minutes: float
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: Literal["low", "medium", "high"]
    geometry: GeoJSONGeometry
    segments: List[SegmentRisk]
    risk_factors: List[RiskFactor]
    data_quality: Literal["complete", "partial", "stale", "unavailable"]


class IncidentAvoidance(BaseModel):
    report_id: str
    category: str
    severity: str
    segment_id: str
    reason: str


class RoutePlanResponse(BaseModel):
    recommended_route_id: str
    risk_source: Literal["baseline", "model"]
    generated_at: str
    routes: List[Route]
    incident_avoidances: List[IncidentAvoidance] = Field(default_factory=list)
