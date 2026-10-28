from typing import Optional
from pydantic import BaseModel, Field
from backend.app.schemas.common import Coordinates


class Alert(BaseModel):
    alert_id: str
    route_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    severity: str = Field(..., json_schema_extra={"example": "high"})
    title: str
    message: str
    location: Optional[Coordinates] = None
    distance_to_risk_km: Optional[float] = None
    created_at: str


class AlertSubscribeRequest(BaseModel):
    email: str = Field(..., json_schema_extra={"example": "transport.officer@domain.gov.in"})
    route_id: str = Field(..., json_schema_extra={"example": "route-1"})
    threshold_risk_score: Optional[int] = Field(default=65, ge=0, le=100)


class AlertSubscribeResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "subscribed"})
    subscription_id: str
    email: str
    route_id: str
    threshold_risk_score: int
    message: str
