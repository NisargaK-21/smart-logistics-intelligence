from pydantic import BaseModel, Field


class ModuleStatus(BaseModel):
    gis: str = Field(..., json_schema_extra={"example": "ok"})
    risk: str = Field(..., json_schema_extra={"example": "ok"})
    weather: str = Field(..., json_schema_extra={"example": "degraded"})


class HealthResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "ok"})
    modules: ModuleStatus
