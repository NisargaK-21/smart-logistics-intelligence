"""Pydantic schemas for ML Hazard Prediction service (NER-ResQ).

Provides validation schemas for:
- Point-level and batch Landslide Susceptibility requests and responses.
- Relative Spatial Susceptibility Index (RSSI) and Landslide Susceptibility Score (LSS).
- Contributing explainable geomorphic factors.
- Model architecture and multi-strategy evaluation metadata inspection.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class FactorContribution(BaseModel):
    factor: str = Field(..., description="Name of the physical or infrastructure hazard factor")
    importance_weight: float = Field(..., description="Global model feature importance weight (0.0 to 1.0)")
    value: float = Field(..., description="Observed feature value for this location")
    contribution: float = Field(..., description="Estimated risk contribution points")
    detail: str = Field(..., description="Human-readable domain explanation of hazard contribution")


class LandslidePredictionRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    slope_deg: Optional[float] = Field(default=None, ge=0.0, le=90.0, description="Terrain slope in degrees (sampled from DEM if omitted)")
    ruggedness: Optional[float] = Field(default=None, ge=0.0, description="Terrain Ruggedness Index (sampled from DEM if omitted)")
    elevation_m: Optional[float] = Field(default=None, description="Elevation in meters (sampled from DEM if omitted)")
    road_distance_m: Optional[float] = Field(default=50.0, ge=0.0, description="Distance to nearest road cut in meters")
    road_class: Optional[str] = Field(default="secondary", description="Road classification (e.g. national_highway, secondary, local)")


class LandslidePredictionResponse(BaseModel):
    latitude: float
    longitude: float
    susceptibility_score: int = Field(..., ge=0, le=100, description="Landslide Susceptibility Score (LSS, 0 to 100)")
    landslide_susceptibility_score: int = Field(..., ge=0, le=100, description="Landslide Susceptibility Score (LSS, 0 to 100)")
    relative_spatial_susceptibility_index: float = Field(..., ge=0.0, le=1.0, description="Relative Spatial Susceptibility Index (RSSI, 0.0 to 1.0). Static spatial propensity, NOT event probability.")
    calibrated_probability: float = Field(..., ge=0.0, le=1.0, description="Deprecated alias for relative_spatial_susceptibility_index (RSSI). Represents relative spatial propensity (0.0 to 1.0), NOT an empirical probability of event occurrence.")
    susceptibility_level: Literal["low", "moderate", "high", "very_high"]
    model_source: str = Field(..., description="Model identifier (e.g. calibrated_random_forest)")
    contributing_factors: List[FactorContribution] = Field(default_factory=list)
    data_quality: Literal["complete", "partial", "stale", "unavailable"]
    warnings: List[str] = Field(default_factory=list)


class BatchLandslidePredictionRequest(BaseModel):
    points: List[LandslidePredictionRequest] = Field(..., min_length=1, max_length=500)


class BatchLandslidePredictionResponse(BaseModel):
    total_points: int
    predictions: List[LandslidePredictionResponse]


class ModelEvaluationMetrics(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    macro_f1: float
    roc_auc: float
    pr_auc: float
    brier_score: float
    confusion_matrix: Dict[str, int]


class ModelInfoResponse(BaseModel):
    available: bool
    status: str
    model_type: Optional[str] = None
    task: Optional[str] = None
    scientific_framework: Optional[Dict[str, Any]] = None
    dataset_provenance: Optional[Dict[str, Any]] = None
    spatial_validation_design: Optional[Dict[str, Any]] = None
    spatial_evaluation_design: Optional[Dict[str, Any]] = None
    holdout_test_metrics: Optional[ModelEvaluationMetrics] = None
    feature_importances: Optional[Dict[str, float]] = None
    bias_analysis: Optional[Dict[str, Any]] = None
    benchmarks: Optional[Dict[str, Any]] = None
