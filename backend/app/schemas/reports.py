from typing import Optional
from pydantic import BaseModel, Field
from backend.app.schemas.common import Coordinates


class FieldReportCreate(BaseModel):
    category: str = Field(..., description="e.g. landslide, flood, road_blockage, accident")
    severity: str = Field(..., description="low, medium, high, critical")
    location: Coordinates
    description: str = Field(..., min_length=3)
    photo_url: Optional[str] = None
    reporter_name: Optional[str] = "Field Officer"


class FieldReport(BaseModel):
    report_id: str
    category: str
    severity: str
    location: Coordinates
    description: str
    photo_url: Optional[str] = None
    reporter_name: Optional[str] = None
    created_at: str
