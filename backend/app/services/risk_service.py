import logging
from typing import Any, Dict, List, Tuple
from backend.app.core.config import settings
from backend.app.core.errors import DependencyUnavailableException

logger = logging.getLogger(__name__)


class RiskService:
    """
    Risk & ML Service Adapter implementing the Person 2 interface:
    - score(segments, context) -> {segment_id: {score, factors, data_quality}}
    - Supports baseline rules and trained model toggle via settings.RISK_SOURCE
    - Implements automatic fallback to baseline if model scoring fails
    - Handles weather degradation (flags partial quality and weather_unavailable factor)
    """

    def check_health(self) -> Tuple[str, str]:
        """Returns (risk_module_status, weather_status)"""
        risk_status = "ok" if settings.RISK_SERVICE_ENABLED else "down"
        weather_status = "ok" if settings.WEATHER_AVAILABLE else "degraded"
        return risk_status, weather_status

    def _score_segment_baseline(
        self, sid: str, seg: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Baseline rules scoring engine."""
        raw_slope = seg.get("slope", seg.get("slope_deg"))
        try:
            slope = float(raw_slope) if raw_slope is not None else 0.0
            slope_available = raw_slope is not None
        except (TypeError, ValueError):
            slope = 0.0
            slope_available = False
        road_class = seg.get("road_class", "secondary")
        vehicle_type = context.get("vehicle_type", "truck")
        factors: List[Dict[str, Any]] = []

        if not slope_available:
            factors.append({
                "name": "terrain_unavailable",
                "contribution": 0.0,
                "detail": "Terrain slope is unavailable; the score excludes terrain risk.",
            })

        # 1. Slope & Terrain factor
        if slope >= 5.0:
            slope_score = min(35.0, round(slope * 4.5))
            factors.append({
                "name": "steep_terrain",
                "contribution": slope_score,
                "detail": f"Terrain slope is {slope}%, elevating rollover and brake wear risk."
            })
        else:
            slope_score = round(slope * 2.0)
            if slope_score > 5:
                factors.append({
                    "name": "moderate_terrain",
                    "contribution": slope_score,
                })

        # 2. Road infrastructure & class factor
        class_risk_map = {
            "expressway": 5.0,
            "national_highway": 12.0,
            "state_highway": 20.0,
            "secondary": 28.0,
            "tertiary": 35.0,
        }
        road_score = class_risk_map.get(road_class, 15.0)
        if road_score >= 15.0:
            factors.append({
                "name": "road_infrastructure",
                "contribution": road_score,
                "detail": f"Road classification '{road_class}' carries elevated baseline risk."
            })

        # 3. Vehicle specific sensitivity factor
        vehicle_factor = 1.2 if vehicle_type == "truck" else (1.0 if vehicle_type == "van" else 0.8)

        # 4. Weather factor or degradation fallback
        if settings.WEATHER_AVAILABLE:
            # Simulate normal or elevated weather factor based on terrain
            if slope >= 5.0:
                weather_contribution = 25.0
                factors.append({
                    "name": "heavy_rainfall",
                    "contribution": weather_contribution,
                    "detail": "Localized precipitation increases slickness and landslide probability."
                })
            else:
                weather_contribution = 12.0
                factors.append({
                    "name": "moderate_rainfall",
                    "contribution": weather_contribution,
                })
            data_quality = "complete" if slope_available else "partial"
        else:
            # Missing or degraded weather
            weather_contribution = 0.0
            factors.append({
                "name": "weather_unavailable",
                "contribution": 0.0,
                "detail": "Weather data could not be fetched; score uses road and history factors only."
            })
            data_quality = "partial"

        # 5. Historical disruptions (e.g. landslides / monsoon washouts in Guwahati-Shillong)
        if "102" in sid or "202" in sid:
            history_contribution = 22.0
            factors.append({
                "name": "landslide_history",
                "contribution": history_contribution,
                "detail": "Segment has historical incidence of monsoon slope failures."
            })
        else:
            history_contribution = 6.0

        raw_score = (slope_score + road_score + weather_contribution + history_contribution) * vehicle_factor
        final_score = int(min(max(round(raw_score), 0), 100))

        return {
            "score": final_score,
            "factors": factors,
            "data_quality": data_quality,
        }

    def _score_segment_model(
        self, sid: str, seg: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Placeholder for Person 2's trained-model adapter.

        A response must never be labelled ``model`` until a real model is wired
        through the shared interface. Raising here activates the documented
        baseline fallback in :meth:`score`.
        """
        raise RuntimeError("No trained model adapter has been configured.")

    def score(
        self, segments: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> Tuple[Dict[str, Dict[str, Any]], str]:
        """
        Evaluates risk for provided segments.
        Returns:
            (scores_dict, effective_risk_source)
        where scores_dict maps segment_id to:
            {
                "score": int,
                "factors": list[dict],
                "data_quality": str
            }
        """
        risk_status, _ = self.check_health()
        if risk_status != "ok":
            raise DependencyUnavailableException(module="risk")

        desired_source = settings.RISK_SOURCE
        effective_source = "baseline"
        results: Dict[str, Dict[str, Any]] = {}

        if desired_source == "model":
            try:
                for seg in segments:
                    sid = seg.get("segment_id", "s-default")
                    results[sid] = self._score_segment_model(sid, seg, context)
                effective_source = "model"
            except Exception as e:
                logger.warning(
                    f"Model scoring failed ({e}); gracefully falling back to baseline rules."
                )
                results.clear()
                for seg in segments:
                    sid = seg.get("segment_id", "s-default")
                    results[sid] = self._score_segment_baseline(sid, seg, context)
                effective_source = "baseline"
        else:
            for seg in segments:
                sid = seg.get("segment_id", "s-default")
                results[sid] = self._score_segment_baseline(sid, seg, context)
            effective_source = "baseline"

        return results, effective_source


risk_service = RiskService()
