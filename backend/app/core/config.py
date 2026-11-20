import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[2] / "smart_logistics.db"


class Settings(BaseModel):
    API_V1_STR: str = Field(default_factory=lambda: os.getenv("API_V1_STR", "/api/v1"))
    PROJECT_NAME: str = Field(default_factory=lambda: os.getenv("PROJECT_NAME", "Smart Logistics Intelligence API"))
    VERSION: str = Field(default_factory=lambda: os.getenv("VERSION", "1.0.0"))
    DATABASE_URL: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
        )
    )

    OSRM_ROUTER_URL: str = Field(
        default_factory=lambda: os.getenv(
            "OSRM_ROUTER_URL", "https://router.project-osrm.org"
        )
    )

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
    TERRAIN_ENABLED: bool = Field(
        default_factory=lambda: os.getenv("TERRAIN_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    TERRAIN_DATA_DIR: str = Field(
        default_factory=lambda: os.getenv(
            "TERRAIN_DATA_DIR",
            str(Path(__file__).resolve().parents[3] / "ml" / "data" / "processed" / "terrain"),
        )
    )


settings = Settings()
