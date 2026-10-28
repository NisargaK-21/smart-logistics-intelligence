from typing import List
from pydantic import BaseModel, Field


class RouteRiskSummary(BaseModel):
    route_id: str
    risk_score: int
    risk_level: str
    active_vehicles: int


class DashboardSummary(BaseModel):
    active_alerts_count: int = Field(..., json_schema_extra={"example": 3})
    recent_reports_count: int = Field(..., json_schema_extra={"example": 12})
    active_vehicles_count: int = Field(..., json_schema_extra={"example": 5})
    overall_system_status: str = Field(..., json_schema_extra={"example": "operational"})
    risk_by_route: List[RouteRiskSummary]
    high_risk_zones_count: int = Field(..., json_schema_extra={"example": 2})
