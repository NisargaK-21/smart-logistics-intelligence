from typing import Optional
from pydantic import BaseModel, Field


class VehicleSimulateRequest(BaseModel):
    vehicle_id: str = Field(..., json_schema_extra={"example": "V001"})
    route_id: str = Field(..., json_schema_extra={"example": "route-1"})
    speed_kmh: Optional[float] = Field(default=45.0, ge=10.0, le=120.0)


class VehicleSimulateResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "started"})
    vehicle_id: str
    route_id: str
    total_waypoints: int
    message: str


class VehiclePosition(BaseModel):
    vehicle_id: str
    lat: float
    lng: float
    speed_kmh: float
    heading_deg: Optional[float] = 0.0
    ts: str
