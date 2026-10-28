import os
from typing import List
from pydantic import BaseModel, Field


class Settings(BaseModel):
    API_V1_STR: str = Field(default_factory=lambda: os.getenv("API_V1_STR", "/api/v1"))
    PROJECT_NAME: str = Field(default_factory=lambda: os.getenv("PROJECT_NAME", "Smart Logistics Intelligence API"))
    VERSION: str = Field(default_factory=lambda: os.getenv("VERSION", "1.0.0"))

    # Study area bounding box: [minLng, minLat, maxLng, maxLat]
    # Covers the Guwahati - Shillong corridor (Assam - Meghalaya region)
    STUDY_AREA_BBOX: List[float] = Field(default_factory=lambda: [90.0, 25.0, 93.0, 27.0])

    # Supported vehicle types
    SUPPORTED_VEHICLE_TYPES: List[str] = Field(default_factory=lambda: ["truck", "van", "car"])

    # Risk scoring engine source: "baseline" (rules) or "model" (ML trained model)
    RISK_SOURCE: str = Field(default_factory=lambda: os.getenv("RISK_SOURCE", "baseline"))

    # Dependency health & simulation controls (used for testing degradation/outages)
    GIS_SERVICE_ENABLED: bool = Field(
        default_factory=lambda: os.getenv("GIS_SERVICE_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    RISK_SERVICE_ENABLED: bool = Field(
        default_factory=lambda: os.getenv("RISK_SERVICE_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    WEATHER_AVAILABLE: bool = Field(
        default_factory=lambda: os.getenv("WEATHER_AVAILABLE", "true").lower() in ("true", "1", "yes")
    )


settings = Settings()
