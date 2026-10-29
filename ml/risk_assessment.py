"""Risk scoring for route segments using weather, road attributes, and optional
historical-disaster context.

The module intentionally integrates with Person 1's routing output without altering
its algorithm. It accepts real `SegmentRecord` instances, dictionaries from
`routing.get_segments`, or route-like objects and preserves each `segment_id` in
all assessments.
"""

from __future__ import annotations

import csv
import math
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from routing.service import get_segments

try:
    from .weather_risk_baseline import calculate_weather_risk
except ImportError:  # pragma: no cover - supports direct script execution.
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from weather_risk_baseline import calculate_weather_risk

ML_ROOT = Path(__file__).resolve().parent
WEATHER_LOCATIONS_PATH = ML_ROOT / "data" / "processed" / "weather_locations.csv"
HISTORICAL_WEATHER_RECORDS_PATH = ML_ROOT / "data" / "processed" / "weather_processed.csv"
RECENT_WEATHER_RECORDS_PATH = ML_ROOT / "data" / "processed" / "weather_recent_oct2026_features.csv"
LANDSLIDE_PATH = ML_ROOT / "data" / "final" / "historical" / "gsi_landslides_ner_validated.csv"
FLOOD_PATH = ML_ROOT / "data" / "final" / "historical" / "cwc_floods_ner_clean.csv"
DEFAULT_MAX_STALE_HOURS = 24.0


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(value):
        return None
    return value


def _normalize_segment_id(segment: Any) -> str:
    if hasattr(segment, "segment_id"):
        value = getattr(segment, "segment_id")
    elif isinstance(segment, dict):
        value = segment.get("segment_id") or segment.get("id") or segment.get("road_id")
    else:
        value = segment
    return str(value) if value is not None else "unknown"


def _as_mapping(segment: Any) -> dict[str, Any]:
    if isinstance(segment, dict):
        return dict(segment)
    if hasattr(segment, "as_dict"):
        return segment.as_dict()
    if hasattr(segment, "__dict__"):
        return vars(segment).copy()
    raise TypeError(f"Unsupported segment object: {type(segment)!r}")


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                try:
                    parsed = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
            else:
                return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def _coerce_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _segment_coordinates(segment: dict[str, Any]) -> tuple[float, float] | None:
    coordinates = segment.get("coordinates")
    if not coordinates:
        return None
    if isinstance(coordinates, list) and coordinates and isinstance(coordinates[0], (list, tuple)):
        try:
            lng, lat = coordinates[0]
            return float(lat), float(lng)
        except (TypeError, ValueError, IndexError):
            return None
    return None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius_km * math.asin(math.sqrt(a))


def _risk_level_from_score(score: float | None) -> str:
    if score is None:
        return "UNKNOWN"
    if score >= 70:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


@lru_cache(maxsize=1)
def _load_weather_locations() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not WEATHER_LOCATIONS_PATH.exists():
        return rows
    with WEATHER_LOCATIONS_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            lat = _as_float(row.get("latitude"))
            lon = _as_float(row.get("longitude"))
            if lat is None or lon is None:
                continue
            rows.append({
                "location_id": row.get("location_id"),
                "latitude": lat,
                "longitude": lon,
            })
    return rows


@lru_cache(maxsize=1)
def _load_historical_weather_records() -> list[dict[str, Any]]:
    return _load_weather_records_from_path(HISTORICAL_WEATHER_RECORDS_PATH)


@lru_cache(maxsize=1)
def _load_recent_weather_records() -> list[dict[str, Any]]:
    return _load_weather_records_from_path(RECENT_WEATHER_RECORDS_PATH)


def _load_weather_records_from_path(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row_copy = {"location_id": row.get("location_id"), "time": _parse_datetime(row.get("time"))}
            for key in (
                "temperature_c",
                "relative_humidity_pct",
                "precipitation_mm",
                "cloud_cover_pct",
                "wind_speed_kmh",
                "precipitation_sum_3h_mm",
                "precipitation_sum_6h_mm",
                "precipitation_sum_24h_mm",
            ):
                row_copy[key] = _as_float(row.get(key))
            rows.append(row_copy)
    return rows


@lru_cache(maxsize=1)
def _load_landslide_points() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not LANDSLIDE_PATH.exists():
        return rows
    with LANDSLIDE_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            lat = _as_float(row.get("latitude"))
            lon = _as_float(row.get("longitude"))
            if lat is None or lon is None:
                continue
            rows.append({"latitude": lat, "longitude": lon, "source": row.get("source")})
    return rows


def _resolve_weather_records(context: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    explicit_records = context.get("weather_records")
    if explicit_records is not None:
        return list(explicit_records), "explicit"

    as_of = _parse_datetime(context.get("as_of")) if context.get("as_of") is not None else None
    if as_of is not None:
        recent_records = _load_recent_weather_records()
        if recent_records and RECENT_WEATHER_RECORDS_PATH.exists():
            recent_start = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
            recent_end = datetime(2026, 10, 3, 23, 0, tzinfo=timezone.utc)
            if recent_start <= as_of <= recent_end:
                return recent_records, "recent_weather_features"
        return _load_historical_weather_records(), "historical_weather"

    recent_records = _load_recent_weather_records()
    if recent_records:
        return recent_records, "recent_weather_features"
    return _load_historical_weather_records(), "historical_weather"


def _sanitize_weather_payload(weather: dict[str, Any]) -> dict[str, Any]:
    required = [
        "precipitation_mm",
        "precipitation_sum_3h_mm",
        "precipitation_sum_6h_mm",
        "precipitation_sum_24h_mm",
        "wind_speed_kmh",
    ]
    sanitized: dict[str, Any] = {}
    for key in required:
        value = weather.get(key)
        if value is None:
            sanitized[key] = None
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            sanitized[key] = None
            continue
        if math.isnan(numeric):
            sanitized[key] = None
        else:
            sanitized[key] = numeric
    return sanitized


def _nearest_weather_for_segment(
    segment: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = context or {}
    coordinates = _segment_coordinates(segment)
    if coordinates is None:
        return {
            "weather_available": False,
            "weather_complete": False,
            "status": "missing_coordinates",
            "weather_risk": None,
            "nearest_station_km": None,
            "weather_time": None,
            "observation_age_hours": None,
            "stale": None,
            "source_dataset": None,
            "notes": ["Segment has no valid coordinates for weather matching."],
        }

    weather_locations = context.get("weather_locations") or _load_weather_locations()
    if not weather_locations:
        return {
            "weather_available": False,
            "weather_complete": False,
            "status": "missing_weather_locations",
            "weather_risk": None,
            "nearest_station_km": None,
            "weather_time": None,
            "observation_age_hours": None,
            "stale": None,
            "source_dataset": None,
            "notes": ["Weather location metadata is unavailable."],
        }

    weather_records, source_dataset = _resolve_weather_records(context)
    if not weather_records:
        return {
            "weather_available": False,
            "weather_complete": False,
            "status": "missing_weather_records",
            "weather_risk": None,
            "nearest_station_km": None,
            "weather_time": None,
            "observation_age_hours": None,
            "stale": None,
            "source_dataset": source_dataset,
            "notes": ["Weather records are unavailable for segment matching."],
        }

    lat, lon = coordinates
    nearest = min(
        weather_locations,
        key=lambda row: _haversine_km(lat, lon, float(row["latitude"]), float(row["longitude"])),
    )
    nearest_km = _haversine_km(lat, lon, float(nearest["latitude"]), float(nearest["longitude"]))
    station_id = nearest.get("location_id")

    matches = [
        row for row in weather_records if str(row.get("location_id")) == str(station_id)
    ]
    if not matches:
        return {
            "weather_available": False,
            "weather_complete": False,
            "status": "station_without_records",
            "weather_risk": None,
            "nearest_station_km": round(nearest_km, 3),
            "weather_time": None,
            "observation_age_hours": None,
            "stale": None,
            "source_dataset": source_dataset,
            "notes": ["Nearest weather station has no records."],
        }

    as_of = _coerce_utc(_parse_datetime(context.get("as_of"))) if context.get("as_of") is not None else None
    observations = []
    for row in matches:
        time_value = _coerce_utc(row.get("time"))
        if time_value is None:
            continue
        if as_of is not None and time_value > as_of:
            continue
        observations.append((time_value, row))

    if not observations:
        return {
            "weather_available": False,
            "weather_complete": False,
            "status": "future_only",
            "weather_risk": None,
            "nearest_station_km": round(nearest_km, 3),
            "weather_time": None,
            "observation_age_hours": None,
            "stale": None,
            "source_dataset": source_dataset,
            "notes": ["Only future observations are available relative to as_of."],
        }

    chosen_time, chosen = max(observations, key=lambda item: item[0])[0], max(observations, key=lambda item: item[0])[1]
    weather_payload = _sanitize_weather_payload({
        key: chosen.get(key)
        for key in (
            "precipitation_mm",
            "precipitation_sum_3h_mm",
            "precipitation_sum_6h_mm",
            "precipitation_sum_24h_mm",
            "wind_speed_kmh",
        )
    })
    weather_risk = calculate_weather_risk(weather_payload)
    age_hours = None
    stale = False
    if as_of is not None:
        age_hours = max((as_of - chosen_time).total_seconds() / 3600.0, 0.0)
        stale = age_hours > DEFAULT_MAX_STALE_HOURS

    weather_complete = weather_risk.get("risk_score") is not None and not stale
    return {
        "weather_available": True,
        "weather_complete": weather_complete,
        "status": "matched" if weather_complete else ("stale" if stale else "incomplete"),
        "weather_risk": weather_risk,
        "nearest_station_km": round(nearest_km, 3),
        "weather_time": chosen_time,
        "observation_age_hours": round(age_hours, 2) if age_hours is not None else None,
        "stale": stale,
        "source_dataset": source_dataset,
        "location_id": station_id,
        "notes": ["Observation is older than 24 hours relative to as_of."] if stale else [],
    }


def _historical_exposure_for_segment(segment: dict[str, Any]) -> dict[str, Any]:
    coordinates = _segment_coordinates(segment)
    if coordinates is None:
        return {
            "historical_data_available": False,
            "nearest_landslide_km": None,
            "landslide_exposure": 0,
            "reasons": ["Segment coordinates are missing; historical exposure cannot be checked."],
        }

    lat, lon = coordinates
    landslides = _load_landslide_points()
    nearest_distance = None
    for event in landslides:
        distance_km = _haversine_km(lat, lon, float(event["latitude"]), float(event["longitude"]))
        if nearest_distance is None or distance_km < nearest_distance:
            nearest_distance = distance_km

    if nearest_distance is None:
        return {
            "historical_data_available": False,
            "nearest_landslide_km": None,
            "landslide_exposure": 0,
            "reasons": ["Historical landslide data is not available on disk."],
        }

    if nearest_distance <= 15:
        exposure = 18
        reason = "Segment is within 15 km of a validated historical landslide point."
    elif nearest_distance <= 40:
        exposure = 8
        reason = "Segment is near a historical landslide location."
    else:
        exposure = 0
        reason = "No nearby historical landslide exposure identified."

    return {
        "historical_data_available": True,
        "nearest_landslide_km": round(nearest_distance, 3),
        "landslide_exposure": exposure,
        "reasons": [reason],
    }


def _road_adjustment(segment: dict[str, Any]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    road_class = str(segment.get("road_class") or "unknown").lower()
    if road_class in {"local", "unknown"}:
        score += 8
        reasons.append("Local or unknown road class can reduce reliability.")
    if road_class == "collector":
        score += 4
        reasons.append("Collector roads carry more local disruption risk than major roads.")

    slope = _as_float(segment.get("slope_deg"))
    if slope is not None:
        if slope >= 15:
            score += 15
            reasons.append(f"Steep slope ({slope:.1f}°) increases landslide risk.")
        elif slope >= 8:
            score += 8
            reasons.append(f"Elevated slope ({slope:.1f}°) increases risk.")
    surface = str(segment.get("surface") or "").lower()
    if surface and surface in {"gravel", "dirt", "mud", "unpaved", "earth"}:
        score += 6
        reasons.append(f"Road surface is {surface}, which increases disruption risk.")

    return score, reasons


def _coerce_segment_list(segments: Any) -> list[dict[str, Any]]:
    if segments is None:
        return []
    if isinstance(segments, dict):
        if "segment_ids" in segments:
            items = segments.get("segments") or []
            if items:
                return [_as_mapping(item) for item in items]
            return []
        return [_as_mapping(segments)]
    if not isinstance(segments, list):
        raise TypeError("segments must be a list of segment objects or a route dict.")
    normalized: list[dict[str, Any]] = []
    for item in segments:
        normalized.append(dict(item) if isinstance(item, dict) else _as_mapping(item))
    return normalized


def score_segments(segments: Any, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Score a list of routing segments while preserving the original `segment_id`."""
    context = context or {}
    results: list[dict[str, Any]] = []
    for segment in _coerce_segment_list(segments):
        segment_id = _normalize_segment_id(segment)
        weather_match = _nearest_weather_for_segment(segment, context)
        historical = _historical_exposure_for_segment(segment)

        reason_list: list[str] = []
        weather_score = None
        if weather_match["weather_risk"] is not None:
            weather_score = float(weather_match["weather_risk"].get("risk_score") or 0.0)
            reason_list.extend(weather_match["weather_risk"].get("reasons") or [])
        else:
            reason_list.extend(weather_match.get("notes") or [])

        road_score, road_reasons = _road_adjustment(segment)
        reason_list.extend(road_reasons)
        reason_list.extend(historical.get("reasons") or [])

        component_scores = {
            "weather": weather_match["weather_risk"].get("risk_score") if weather_match["weather_risk"] else None,
            "historical_disaster": historical.get("landslide_exposure"),
            "road": road_score,
        }

        risk_complete = bool(
            weather_match.get("weather_complete", False)
            and _segment_coordinates(segment) is not None
        )

        total = 0.0
        total += weather_score or 0.0
        total += float(historical.get("landslide_exposure") or 0.0)
        total += float(road_score)
        total = min(total, 100.0)

        result = {
            "segment_id": segment_id,
            "risk_score": round(total, 1) if risk_complete else None,
            "risk_level": _risk_level_from_score(total) if risk_complete else "UNKNOWN",
            "risk_complete": risk_complete,
            "component_scores": component_scores,
            "hazard_indicators": {
                "weather": weather_match.get("weather_risk"),
                "historical_disaster": {
                    "nearest_landslide_km": historical.get("nearest_landslide_km"),
                    "landslide_exposure": historical.get("landslide_exposure"),
                },
                "road": {
                    "road_class": segment.get("road_class"),
                    "slope_deg": segment.get("slope_deg"),
                    "surface": segment.get("surface"),
                    "is_oneway": segment.get("is_oneway"),
                },
            },
            "reasons": reason_list or ["No risk triggers were found for this segment."],
            "data_quality": {
                "weather_data_available": weather_match.get("weather_available", False),
                "weather_complete": weather_match.get("weather_complete", False),
                "historical_data_available": historical.get("historical_data_available", False),
                "coordinates_available": _segment_coordinates(segment) is not None,
                "nearest_weather_station_km": weather_match.get("nearest_station_km"),
                "weather_time": weather_match.get("weather_time"),
                "observation_age_hours": weather_match.get("observation_age_hours"),
                "stale": weather_match.get("stale", False),
                "source_dataset": weather_match.get("source_dataset"),
            },
            "matching": {
                "weather_status": weather_match.get("status"),
                "nearest_station_km": weather_match.get("nearest_station_km"),
                "location_id": weather_match.get("location_id"),
            },
        }
        results.append(result)
    return results


def score_route(route: dict[str, Any] | Any, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Score a single route candidate and keep the route/segment relationship."""
    context = context or {}
    if isinstance(route, dict):
        route_id = route.get("route_id") or "route-1"
        segment_ids = route.get("segment_ids") or []
        segments = context.get("segments") or []
        if not segments and segment_ids:
            try:
                segments = get_segments(segment_ids)
            except Exception:
                segments = [{"segment_id": sid} for sid in segment_ids]
    else:
        route_id = getattr(route, "route_id", "route-1")
        segment_ids = list(getattr(route, "segment_ids", []) or [])
        segments = list(getattr(route, "segments", []) or [])
        if not segments and segment_ids:
            try:
                segments = get_segments(segment_ids)
            except Exception:
                segments = [{"segment_id": sid} for sid in segment_ids]

    assessments = score_segments(segments, context)
    if not assessments:
        return {
            "route_id": route_id,
            "risk_score": None,
            "risk_level": "UNKNOWN",
            "overall_risk_complete": False,
            "segment_ids": segment_ids,
            "segments": [],
        }

    complete = all(item.get("risk_complete", False) for item in assessments)
    if complete:
        route_score = round(sum(item["risk_score"] for item in assessments) / len(assessments), 1)
        route_level = _risk_level_from_score(route_score)
    else:
        route_score = None
        route_level = "UNKNOWN"

    return {
        "route_id": route_id,
        "risk_score": route_score,
        "risk_level": route_level,
        "overall_risk_complete": complete,
        "segment_ids": segment_ids,
        "segments": assessments,
    }


def score_routes(routes: list[Any], context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Score multiple route candidates without rebuilding the routing graph."""
    context = context or {}
    return [score_route(route, context) for route in routes]


__all__ = [
    "score_route",
    "score_routes",
    "score_segments",
]
