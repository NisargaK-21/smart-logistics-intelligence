"""Landslide Susceptibility ML Prediction Service for NER-ResQ.

Objective 1: Strengthen genuine ML-based hazard prediction using real historical
disaster records (GSI), high-resolution Copernicus GLO-30 DEM, and road attributes.

Scientific Principles:
- Computes Relative Spatial Susceptibility Index (RSSI, 0.0-1.0) and Landslide Susceptibility Score (LSS, 0-100).
- Static geomorphological propensity mapping, NOT an event occurrence probability or temporal forecast.
- Unconstrained background pseudo-absences benchmarked alongside hard negative slopes.
- Factor contributions and geomorphological explainability.
- Explicit warnings for out-of-DEM-coverage queries.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

ML_ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = ML_ROOT / "models" / "landslide_susceptibility_rf.joblib"


class LandslideSusceptibilityService:
    """Production ML Service for estimating relative terrain landslide susceptibility."""

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or DEFAULT_MODEL_PATH
        self._pipeline = None
        self._metadata: Dict[str, Any] = {}
        self._feature_importances: Dict[str, float] = {}
        self._loaded = False
        self._terrain_service = None
        self._load_model()

    def _get_terrain_service(self):
        if self._terrain_service is None:
            try:
                from backend.app.services.terrain_service import TerrainService
                self._terrain_service = TerrainService()
            except Exception as e:
                logger.warning("Could not initialize TerrainService: %s", e)
        return self._terrain_service

    def _load_model(self) -> bool:
        if not self.model_path.is_file():
            logger.warning("Landslide susceptibility model artifact not found at %s", self.model_path)
            self._loaded = False
            return False

        try:
            payload = joblib.load(self.model_path)
            self._pipeline = payload.get("pipeline")
            self._metadata = payload.get("metadata", {})
            self._feature_importances = payload.get("feature_importances", {})
            self._loaded = True
            logger.info("Successfully loaded Landslide Susceptibility model from %s", self.model_path)
            return True
        except Exception as exc:
            logger.error("Failed to load landslide susceptibility model: %s", exc)
            self._loaded = False
            return False

    @property
    def is_available(self) -> bool:
        return self._loaded and self._pipeline is not None

    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata, evaluation metrics, and feature importances."""
        if not self.is_available:
            return {
                "available": False,
                "status": "Model artifact not loaded",
            }

        prod_eval = self._metadata.get("production_model_evaluation", {})
        holdout_metrics = prod_eval.get("metrics")
        if holdout_metrics is None:
            # Fallback for alternative structures
            holdout_metrics = (
                self._metadata.get("models_evaluated", {})
                .get("calibrated_random_forest", {})
                .get("holdout_test", {})
            )

        features_meta = self._metadata.get("features", {})
        bias_analysis = features_meta.get("bias_analysis", {})

        spatial_design = (
            self._metadata.get("spatial_validation_design")
            or self._metadata.get("spatial_evaluation_design", {})
        )

        return {
            "available": True,
            "status": "operational",
            "model_type": prod_eval.get("model_type", "Calibrated Random Forest (Platt Sigmoid Scaling)"),
            "task": self._metadata.get("task", "Landslide Susceptibility Estimation"),
            "scientific_framework": self._metadata.get("scientific_framework", {}),
            "dataset_provenance": self._metadata.get("dataset_provenance", {}),
            "spatial_validation_design": spatial_design,
            "spatial_evaluation_design": spatial_design,
            "holdout_test_metrics": holdout_metrics,
            "feature_importances": self._feature_importances,
            "bias_analysis": bias_analysis,
            "benchmarks": self._metadata.get("benchmarks", {}),
        }

    def _determine_susceptibility_level(self, score: float) -> str:
        if score < 0.25:
            return "low"
        elif score < 0.50:
            return "moderate"
        elif score < 0.75:
            return "high"
        else:
            return "very_high"

    def _build_explainable_factors(
        self,
        slope: float,
        ruggedness: float,
        elevation: float,
        road_distance_m: float,
        score: float,
    ) -> List[Dict[str, Any]]:
        factors = []

        # 1. Slope Contribution
        slope_weight = self._feature_importances.get("slope_deg", 0.21)
        if slope >= 25.0:
            contrib = round(min(45.0, slope * 1.5), 1)
            factors.append({
                "factor": "extremely_steep_slope",
                "importance_weight": slope_weight,
                "value": round(slope, 1),
                "contribution": contrib,
                "detail": f"Terrain slope is {slope:.1f} degrees (exceeds critical failure threshold of 25 deg).",
            })
        elif slope >= 15.0:
            contrib = round(min(30.0, slope * 1.3), 1)
            factors.append({
                "factor": "steep_slope",
                "importance_weight": slope_weight,
                "value": round(slope, 1),
                "contribution": contrib,
                "detail": f"Terrain slope is {slope:.1f} degrees, elevating gravitational shear stress.",
            })
        elif slope >= 5.0:
            contrib = round(slope * 0.8, 1)
            factors.append({
                "factor": "moderate_slope",
                "importance_weight": slope_weight,
                "value": round(slope, 1),
                "contribution": contrib,
                "detail": f"Terrain slope is {slope:.1f} degrees (moderate undulating relief).",
            })
        else:
            factors.append({
                "factor": "flat_low_slope",
                "importance_weight": slope_weight,
                "value": round(slope, 1),
                "contribution": 0.0,
                "detail": f"Terrain slope is {slope:.1f} degrees (gravitationally stable valley/plain).",
            })

        # 2. Ruggedness Contribution
        rugg_weight = self._feature_importances.get("ruggedness", 0.30)
        if ruggedness >= 12.0:
            contrib = round(min(25.0, ruggedness * 1.5), 1)
            factors.append({
                "factor": "high_terrain_ruggedness",
                "importance_weight": rugg_weight,
                "value": round(ruggedness, 1),
                "contribution": contrib,
                "detail": f"Terrain Ruggedness Index is {ruggedness:.1f}, indicating highly dissected topography.",
            })
        elif ruggedness >= 6.0:
            contrib = round(ruggedness * 1.0, 1)
            factors.append({
                "factor": "moderate_terrain_ruggedness",
                "importance_weight": rugg_weight,
                "value": round(ruggedness, 1),
                "contribution": contrib,
                "detail": f"Terrain Ruggedness Index is {ruggedness:.1f}.",
            })

        # 3. Road Proximity Contribution (Toe excavation hazard + reporting association)
        road_weight = self._feature_importances.get("road_distance_m", 0.28)
        if road_distance_m <= 150.0:
            contrib = 15.0
            factors.append({
                "factor": "road_cut_proximity",
                "importance_weight": road_weight,
                "value": round(road_distance_m, 1),
                "contribution": contrib,
                "detail": f"Location is within {road_distance_m:.1f}m of road cut, prone to slope toe destabilization.",
            })
        elif road_distance_m <= 500.0:
            contrib = 8.0
            factors.append({
                "factor": "road_corridor_proximity",
                "importance_weight": road_weight,
                "value": round(road_distance_m, 1),
                "contribution": contrib,
                "detail": f"Location is {road_distance_m:.1f}m from nearest transportation corridor.",
            })

        factors.sort(key=lambda x: x["contribution"], reverse=True)
        return factors

    def predict_point(
        self,
        lat: float,
        lon: float,
        slope_deg: Optional[float] = None,
        ruggedness: Optional[float] = None,
        elevation_m: Optional[float] = None,
        road_distance_m: float = 50.0,
        road_class: str = "secondary",
    ) -> Dict[str, Any]:
        """Predict relative landslide susceptibility for a single coordinate point."""
        data_quality = "complete"
        warnings = []

        # If terrain metrics are not passed explicitly, sample from Copernicus DEM
        if slope_deg is None or elevation_m is None or ruggedness is None:
            ts = self._get_terrain_service()
            if ts:
                terrain = ts.sample_point(lon, lat)
                if terrain.get("slope_deg") is not None:
                    slope_deg = terrain["slope_deg"] if slope_deg is None else slope_deg
                    elevation_m = terrain["elevation_m"] if elevation_m is None else elevation_m
                    ruggedness = terrain["ruggedness"] if ruggedness is None else ruggedness
                else:
                    data_quality = "partial"
                    warnings.append("Point is outside high-resolution DEM raster coverage; using conservative defaults.")
            else:
                data_quality = "partial"
                warnings.append("TerrainService unavailable; DEM could not be queried.")

        slope_val = float(slope_deg) if slope_deg is not None else 0.0
        elev_val = float(elevation_m) if elevation_m is not None else 100.0
        rugg_val = float(ruggedness) if ruggedness is not None else 0.0
        road_dist_val = float(road_distance_m) if road_distance_m is not None else 50.0
        road_class_val = str(road_class) if road_class else "secondary"

        if not self.is_available or data_quality != "complete":
            # Fallback heuristic if model is not loaded or terrain data is outside DEM coverage
            rssi = min(1.0, max(0.0, (slope_val / 40.0) * 0.7 + (rugg_val / 20.0) * 0.3))
            lss = int(round(rssi * 100))
            fallback_reason = (
                "Trained ML model artifact unavailable; estimated via heuristic fallback."
                if not self.is_available
                else "Location is outside high-resolution DEM coverage; ML prediction unavailable, fallback heuristic score provided."
            )
            return {
                "susceptibility_score": lss,
                "landslide_susceptibility_score": lss,
                "relative_spatial_susceptibility_index": round(rssi, 4),
                "calibrated_probability": round(rssi, 4),
                "susceptibility_level": self._determine_susceptibility_level(rssi),
                "model_source": "heuristic_fallback",
                "contributing_factors": self._build_explainable_factors(slope_val, rugg_val, elev_val, road_dist_val, rssi),
                "data_quality": data_quality,
                "warnings": warnings + [fallback_reason],
            }

        input_row = pd.DataFrame([{
            "slope_deg": slope_val,
            "ruggedness": rugg_val,
            "elevation_m": elev_val,
            "road_distance_m": road_dist_val,
            "road_class": road_class_val,
        }])

        try:
            # Model score represents Relative Spatial Susceptibility Index (RSSI)
            rssi = float(self._pipeline.predict_proba(input_row)[0, 1])
            lss = int(min(max(round(rssi * 100), 0), 100))
            level = self._determine_susceptibility_level(rssi)
            factors = self._build_explainable_factors(slope_val, rugg_val, elev_val, road_dist_val, rssi)

            return {
                "susceptibility_score": lss,
                "landslide_susceptibility_score": lss,
                "relative_spatial_susceptibility_index": round(rssi, 4),
                "calibrated_probability": round(rssi, 4),  # Preserved as backward-compatible alias
                "susceptibility_level": level,
                "model_source": "calibrated_random_forest",
                "contributing_factors": factors,
                "data_quality": data_quality,
                "warnings": warnings,
            }
        except Exception as e:
            logger.warning("ML inference failed (%s); falling back to heuristic score.", e)
            rssi = min(1.0, max(0.0, (slope_val / 40.0) * 0.7 + (rugg_val / 20.0) * 0.3))
            lss = int(round(rssi * 100))
            return {
                "susceptibility_score": lss,
                "landslide_susceptibility_score": lss,
                "relative_spatial_susceptibility_index": round(rssi, 4),
                "calibrated_probability": round(rssi, 4),
                "susceptibility_level": self._determine_susceptibility_level(rssi),
                "model_source": "heuristic_fallback",
                "contributing_factors": self._build_explainable_factors(slope_val, rugg_val, elev_val, road_dist_val, rssi),
                "data_quality": "partial",
                "warnings": warnings + [f"Inference error: {e}"],
            }

    def predict_segments(
        self,
        segments: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Score a list of route segments with ML landslide susceptibility."""
        results = {}
        for seg in segments:
            sid = str(seg.get("segment_id") or seg.get("id") or "seg-default")
            coords = seg.get("coordinates", [])
            lat = float(coords[0][1]) if coords else 25.6
            lon = float(coords[0][0]) if coords else 91.8

            slope = seg.get("slope_deg", seg.get("slope"))
            elevation = seg.get("elevation_m")
            ruggedness = seg.get("ruggedness")
            road_class = seg.get("road_class", "secondary")

            pred = self.predict_point(
                lat=lat,
                lon=lon,
                slope_deg=slope,
                ruggedness=ruggedness,
                elevation_m=elevation,
                road_distance_m=0.0,
                road_class=road_class,
            )
            results[sid] = pred

        return results


# Global singleton instance
landslide_service = LandslideSusceptibilityService()
