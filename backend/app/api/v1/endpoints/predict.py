"""FastAPI endpoints for ML Hazard Prediction service (NER-ResQ).

Provides:
- POST /predict/landslide-susceptibility: Point-level landslide susceptibility prediction.
- POST /predict/batch-landslide-susceptibility: Batch segment/point prediction.
- GET /predict/model-info: Transparent inspection of ML model architecture and spatial holdout evaluation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status

from backend.app.schemas.common import ErrorResponse
from backend.app.schemas.predict import (
    BatchLandslidePredictionRequest,
    BatchLandslidePredictionResponse,
    LandslidePredictionRequest,
    LandslidePredictionResponse,
    ModelInfoResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_landslide_service():
    try:
        from ml.landslide_susceptibility import landslide_service
        return landslide_service
    except Exception as exc:
        logger.error("Could not import LandslideSusceptibilityService: %s", exc)
        return None


@router.post(
    "/landslide-susceptibility",
    response_model=LandslidePredictionResponse,
    summary="Predict calibrated terrain landslide susceptibility for a geographic coordinate",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid coordinates or request payload"},
        500: {"model": ErrorResponse, "description": "Unexpected prediction error"},
    },
)
def predict_landslide_susceptibility(request: LandslidePredictionRequest):
    service = _get_landslide_service()
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Landslide prediction service is currently unavailable.",
        )

    try:
        pred = service.predict_point(
            lat=request.latitude,
            lon=request.longitude,
            slope_deg=request.slope_deg,
            ruggedness=request.ruggedness,
            elevation_m=request.elevation_m,
            road_distance_m=request.road_distance_m or 50.0,
            road_class=request.road_class or "secondary",
        )
        return LandslidePredictionResponse(
            latitude=request.latitude,
            longitude=request.longitude,
            susceptibility_score=pred["susceptibility_score"],
            landslide_susceptibility_score=pred.get("landslide_susceptibility_score", pred["susceptibility_score"]),
            relative_spatial_susceptibility_index=pred.get("relative_spatial_susceptibility_index", pred["calibrated_probability"]),
            calibrated_probability=pred["calibrated_probability"],
            susceptibility_level=pred["susceptibility_level"],
            model_source=pred["model_source"],
            contributing_factors=pred["contributing_factors"],
            data_quality=pred["data_quality"],
            warnings=pred["warnings"],
        )
    except Exception as exc:
        logger.exception("Prediction failed for coordinate (%f, %f): %s", request.latitude, request.longitude, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Landslide susceptibility prediction failed: {exc}",
        )


@router.post(
    "/batch-landslide-susceptibility",
    response_model=BatchLandslidePredictionResponse,
    summary="Batch predict landslide susceptibility across multiple coordinates or road segments",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid batch request payload"},
        500: {"model": ErrorResponse, "description": "Unexpected prediction error"},
    },
)
def batch_predict_landslide_susceptibility(request: BatchLandslidePredictionRequest):
    service = _get_landslide_service()
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Landslide prediction service is currently unavailable.",
        )

    predictions = []
    for pt in request.points:
        pred = service.predict_point(
            lat=pt.latitude,
            lon=pt.longitude,
            slope_deg=pt.slope_deg,
            ruggedness=pt.ruggedness,
            elevation_m=pt.elevation_m,
            road_distance_m=pt.road_distance_m or 50.0,
            road_class=pt.road_class or "secondary",
        )
        predictions.append(
            LandslidePredictionResponse(
                latitude=pt.latitude,
                longitude=pt.longitude,
                susceptibility_score=pred["susceptibility_score"],
                landslide_susceptibility_score=pred.get("landslide_susceptibility_score", pred["susceptibility_score"]),
                relative_spatial_susceptibility_index=pred.get("relative_spatial_susceptibility_index", pred["calibrated_probability"]),
                calibrated_probability=pred["calibrated_probability"],
                susceptibility_level=pred["susceptibility_level"],
                model_source=pred["model_source"],
                contributing_factors=pred["contributing_factors"],
                data_quality=pred["data_quality"],
                warnings=pred["warnings"],
            )
        )

    return BatchLandslidePredictionResponse(
        total_points=len(predictions),
        predictions=predictions,
    )


@router.get(
    "/model-info",
    response_model=ModelInfoResponse,
    summary="Get transparency metadata, independent spatial validation metrics, and feature importances",
)
def get_model_info():
    service = _get_landslide_service()
    if service is None or not service.is_available:
        return ModelInfoResponse(
            available=False,
            status="Model artifact unavailable",
        )

    info = service.get_model_info()
    return ModelInfoResponse(**info)

