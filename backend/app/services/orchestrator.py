from datetime import datetime, timezone
from typing import Any, Dict, List
from backend.app.schemas.route_plan import (
    GeoJSONGeometry,
    RiskFactor,
    Route,
    RoutePlanRequest,
    RoutePlanResponse,
    SegmentRisk,
)
from backend.app.services.gis_service import gis_service
from backend.app.services.risk_service import risk_service


class RouteOrchestrator:
    """
    Central orchestration service (Person 3) that coordinates between
    GIS & Routing (Person 1) and Risk & ML (Person 2).
    """

    def _determine_risk_level(self, score: int) -> str:
        if score <= 33:
            return "low"
        elif score <= 66:
            return "medium"
        else:
            return "high"

    def _determine_data_quality(self, segment_qualities: List[str]) -> str:
        if "unavailable" in segment_qualities:
            return "unavailable"
        if "partial" in segment_qualities:
            return "partial"
        if "stale" in segment_qualities:
            return "stale"
        return "complete"

    def plan_routes(self, request: RoutePlanRequest) -> RoutePlanResponse:
        origin_dict = {"lat": request.origin.lat, "lng": request.origin.lng}
        dest_dict = {"lat": request.destination.lat, "lng": request.destination.lng}

        # 1. Fetch candidate routes from GIS
        candidate_routes = gis_service.find_routes(
            origin=origin_dict,
            destination=dest_dict,
            vehicle_type=request.vehicle_type,
        )

        # 2. Collect all required segment IDs across candidates
        all_segment_ids: List[str] = []
        for cr in candidate_routes:
            for sid in cr.get("segment_ids", []):
                if sid not in all_segment_ids:
                    all_segment_ids.append(sid)

        # 3. Fetch segment attributes from GIS
        segments_data = gis_service.get_segments(all_segment_ids)

        # Build segment payload list for Risk service
        segments_payload = [
            {"segment_id": sid, **attrs} for sid, attrs in segments_data.items()
        ]

        # 4. Score all segments via Risk module
        departure_time = request.departure_time or datetime.now(timezone.utc).astimezone().isoformat()
        context = {
            "vehicle_type": request.vehicle_type,
            "departure_time": departure_time,
        }
        segment_scores, risk_source = risk_service.score(segments_payload, context)

        # 5. Aggregate route-level scores, risk factors, and data quality
        processed_routes: List[Route] = []

        for cr in candidate_routes:
            route_id = cr["route_id"]
            distance_km = float(cr["distance_km"])
            duration_min = float(cr["duration_min"])
            geometry = GeoJSONGeometry(
                type=cr["geometry"].get("type", "LineString"),
                coordinates=cr["geometry"]["coordinates"],
            )

            route_segments: List[SegmentRisk] = []
            segment_qualities: List[str] = []
            factors_map: Dict[str, Dict[str, Any]] = {}

            total_length = 0.0
            weighted_risk_sum = 0.0
            worst_segment_score = 0

            for sid in cr.get("segment_ids", []):
                seg_attr = segments_data.get(sid, {})
                length_km = float(seg_attr.get("length_km", 10.0))
                seg_risk_info = segment_scores.get(sid, {
                    "score": 30,
                    "factors": [],
                    "data_quality": "complete",
                })

                score = int(seg_risk_info["score"])
                seg_coords = seg_attr.get("coordinates", [])

                route_segments.append(
                    SegmentRisk(
                        segment_id=sid,
                        risk_score=score,
                        coordinates=seg_coords,
                    )
                )

                # Weighting calculations
                total_length += length_km
                weighted_risk_sum += length_km * score
                if score > worst_segment_score:
                    worst_segment_score = score

                segment_qualities.append(seg_risk_info.get("data_quality", "complete"))

                # Consolidate factors
                for f in seg_risk_info.get("factors", []):
                    fname = f["name"]
                    fcontrib = float(f.get("contribution", 0.0))
                    fdetail = f.get("detail")
                    if fname not in factors_map:
                        factors_map[fname] = {
                            "contribution": fcontrib,
                            "count": 1,
                            "detail": fdetail,
                        }
                    else:
                        factors_map[fname]["contribution"] += fcontrib
                        factors_map[fname]["count"] += 1
                        if fdetail and not factors_map[fname]["detail"]:
                            factors_map[fname]["detail"] = fdetail

            # Route score formula: 0.7 * length-weighted mean + 0.3 * worst segment
            if total_length > 0:
                length_weighted_mean = weighted_risk_sum / total_length
            else:
                length_weighted_mean = 0.0

            route_risk_score = round(0.7 * length_weighted_mean + 0.3 * worst_segment_score)
            route_risk_score = int(min(max(route_risk_score, 0), 100))
            risk_level = self._determine_risk_level(route_risk_score)
            route_data_quality = self._determine_data_quality(segment_qualities)

            # Compile risk factors list
            compiled_factors: List[RiskFactor] = []
            for fname, fdata in factors_map.items():
                avg_contrib = round(fdata["contribution"] / max(fdata["count"], 1), 1)
                compiled_factors.append(
                    RiskFactor(
                        name=fname,
                        contribution=avg_contrib,
                        detail=fdata["detail"],
                    )
                )

            # Sort factors by contribution descending
            compiled_factors.sort(key=lambda x: x.contribution, reverse=True)

            processed_routes.append(
                Route(
                    route_id=route_id,
                    distance_km=distance_km,
                    estimated_duration_minutes=duration_min,
                    risk_score=route_risk_score,
                    risk_level=risk_level,
                    geometry=geometry,
                    segments=route_segments,
                    risk_factors=compiled_factors,
                    data_quality=route_data_quality,
                )
            )

        # 6. Rank candidate routes:
        # Lowest risk_score first; if tied, lowest distance_km, then lowest estimated_duration_minutes
        processed_routes.sort(
            key=lambda r: (r.risk_score, r.distance_km, r.estimated_duration_minutes)
        )

        recommended_route_id = processed_routes[0].route_id if processed_routes else ""

        now_iso = datetime.now(timezone.utc).astimezone().isoformat()

        return RoutePlanResponse(
            recommended_route_id=recommended_route_id,
            risk_source=risk_source,
            generated_at=now_iso,
            routes=processed_routes,
        )


orchestrator = RouteOrchestrator()
