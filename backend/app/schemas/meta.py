from typing import List
from pydantic import BaseModel, Field


class CoverageResponse(BaseModel):
    bbox: List[float] = Field(
        ...,
        description="[minLng, minLat, maxLng, maxLat]",
        json_schema_extra={"example": [90.0, 25.0, 93.0, 27.0]},
    )
    vehicle_types: List[str] = Field(
        ...,
        json_schema_extra={"example": ["truck", "van", "car"]},
    )
