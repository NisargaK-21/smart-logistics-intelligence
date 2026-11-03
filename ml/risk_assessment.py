"""Risk scoring for route segments using weather, road attributes, and historical-disaster context.

Provides the Person 2 Risk & ML interface expected by the backend orchestrator:
- `score(segments: list[dict], context: dict) -> dict[str, dict]`
- Segment-level risk levels: LOW (0–33), MEDIUM (34–66), HIGH (67–100)
- Explicit data-quality tracking: "complete", "partial", "stale", "unavailable"
- Robust handling of missing, negative, stale, and future-only observations
- Graceful fallback from model predictions to rules-based baseline
- Backward-compatible `score_segments`, `score_route`, and `score_routes`
"""

from __future__ import annotations

import csv
import logging
import math
import pickle
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from routing.service import get_segments

try:
    from .weather_risk_baseline import calculate_weather_risk
    from .risk_model_features import WEATHER_FEATURE_COLUMNS
except ImportError:  # pragma: no cover
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from weather_risk_baseline import calculate_weather_risk
    from risk_model_features import WEATHER_FEATURE_COLUMNS

logger = logging.getLogger(__name__)

ML_ROOT = Path(__file__).resolve().parent
WEATHER_LOCATIONS_PATH = ML_ROOT / "data" / "processed" / "weather_locations.csv"
HISTORICAL_WEATHER_RECORDS_PATH = ML_ROOT / "data" / "processed" / "weather_processed.csv"
RECENT_WEATHER_RECORDS_PATH = ML_ROOT / "data" / "processed" / "weather_recent_oct2026_features.csv"
LANDSLIDE_PATH = ML_ROOT / "data" / "final" / "historical" / "gsi_landslides_ner_validated.csv"
FLOOD_PATH = ML_ROOT / "data" / "final" / "historical" / "cwc_floods_ner_clean.csv"
MODEL_DIR = ML_ROOT / "models"
EXPERIMENTAL_MODEL_PATH = MODEL_DIR / "weather_risk_logistic_regression.joblib"

DEFAULT_MAX_STALE_HOURS = 24.0
MAX_RELIABLE_STATION_DISTANCE_KM = 50.0
MAX_USABLE_STATION_DISTANCE_KM = 150.0
MODEL_CLASS_LABELS = ("LOW", "MEDIUM", "HIGH")
MODEL_ACCEPTANCE_THRESHOLDS = {
    "minimum_test_support_per_class": 20,
    "minimum_macro_f1": 0.80,
    "minimum_accuracy": 0.80,
    "minimum_macro_f1_improvement_over_majority": 0.10,
}


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        val = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(val) or math.isinf(val):
        return None
    return val


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
        # Check flat lat/lng or lon
        lat = _as_float(segment.get("lat") or segment.get("latitude"))
        lng = _as_float(segment.get("lng") or segment.get("lon") or segment.get("longitude"))
        if lat is not None and lng is not None:
            return lat, lng
        return None
    if isinstance(coordinates, list) and coordinates and isinstance(coordinates[0], (list, tuple)):
        try:
            lng, lat = coordinates[0]
            lat_f, lng_f = float(lat), float(lng)
            if math.isnan(lat_f) or math.isnan(lng_f):
                return None
            return lat_f, lng_f
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
    return 2 * radius_km * math.asin(math.sqrt(min(max(a, 0.0), 1.0)))


def _risk_level_from_score(score: float | int | None) -> str:
    """Backend contract aligned risk thresholds: LOW 0-33, MEDIUM 34-66, HIGH 67-100."""
    if score is None:
        return "UNKNOWN"
    if score >= 67:
        return "HIGH"
    if score >= 34:
        return "MEDIUM"
    return "LOW"


def _risk_level_lower(score: int | float | None) -> str:
    """Lowercase risk level string matching API schema."""
    level = _risk_level_from_score(score)
    return level.lower() if level != "UNKNOWN" else "unknown"


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

    as_of = _parse_datetime(context.get("departure_time") or context.get("as_of"))
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
    sanitized: dict[str, Any] = {}
    for key in WEATHER_FEATURE_COLUMNS:
        value = weather.get(key)
        if value is None:
            sanitized[key] = None
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            sanitized[key] = None
            continue
        if math.isnan(numeric) or math.isinf(numeric) or numeric < 0:
            sanitized[key] = None
        else:
            sanitized[key] = numeric
    return sanitized


def _nearest_weather_for_segment(
    segment: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = context or {}

    # Check if weather is explicitly marked unavailable or disabled
    weather_enabled = context.get("weather_available", context.get("weather_enabled", True))
    if weather_enabled is False:
        return {
            "weather_available": False,
            "weather_complete": False,
            "status": "weather_unavailable",
            "weather_risk": None,
            "nearest_station_km": None,
            "weather_time": None,
            "observation_age_hours": None,
            "stale": False,
            "distant": False,
            "source_dataset": None,
            "notes": ["Weather provider is marked unavailable or degraded."],
        }

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
            "distant": False,
            "source_dataset": None,
            "notes": ["Segment has no valid coordinates for weather matching."],
        }

    weather_locations = context.get("weather_locations")
    if weather_locations is None:
        weather_locations = _load_weather_locations()

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
            "distant": False,
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
            "distant": False,
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

    # If the nearest station is completely out of usable range
    if nearest_km > MAX_USABLE_STATION_DISTANCE_KM:
        return {
            "weather_available": False,
            "weather_complete": False,
            "status": "distant_station",
            "weather_risk": None,
            "nearest_station_km": round(nearest_km, 3),
            "weather_time": None,
            "observation_age_hours": None,
            "stale": False,
            "distant": True,
            "source_dataset": source_dataset,
            "location_id": station_id,
            "notes": [f"Nearest station is {nearest_km:.1f} km away (>150 km); weather data unusable."],
        }

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
            "distant": nearest_km > MAX_RELIABLE_STATION_DISTANCE_KM,
            "source_dataset": source_dataset,
            "notes": ["Nearest weather station has no records."],
        }

    as_of = _coerce_utc(_parse_datetime(context.get("departure_time") or context.get("as_of")))
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
            "distant": nearest_km > MAX_RELIABLE_STATION_DISTANCE_KM,
            "source_dataset": source_dataset,
            "notes": ["Only future observations are available relative to departure time."],
        }

    chosen_time, chosen = max(observations, key=lambda item: item[0])
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

    is_distant = nearest_km > MAX_RELIABLE_STATION_DISTANCE_KM
    has_valid_score = weather_risk.get("risk_score") is not None
    weather_complete = has_valid_score and not stale and not is_distant

    notes = []
    if stale:
        notes.append(f"Observation is older than {DEFAULT_MAX_STALE_HOURS:.0f} hours relative to departure time.")
    if is_distant:
        notes.append(f"Nearest weather station is {nearest_km:.1f} km away (>50 km); localized conditions unverified.")

    if weather_complete:
        status = "matched"
    elif stale:
        status = "stale"
    elif is_distant:
        status = "distant_station"
    else:
        status = "incomplete"

    return {
        "weather_available": True,
        "weather_complete": weather_complete,
        "status": status,
        "weather_risk": weather_risk,
        "weather_features": weather_payload,
        "nearest_station_km": round(nearest_km, 3),
        "weather_time": chosen_time,
        "observation_age_hours": round(age_hours, 2) if age_hours is not None else None,
        "stale": stale,
        "distant": is_distant,
        "source_dataset": source_dataset,
        "location_id": station_id,
        "notes": notes,
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
    if not landslides:
        return {
            "historical_data_available": False,
            "nearest_landslide_km": None,
            "landslide_exposure": 0,
            "reasons": ["Historical landslide data is not available on disk."],
        }

    nearest_distance = None
    for event in landslides:
        dist_km = _haversine_km(lat, lon, float(event["latitude"]), float(event["longitude"]))
        if nearest_distance is None or dist_km < nearest_distance:
            nearest_distance = dist_km

    if nearest_distance is None:
        return {
            "historical_data_available": False,
            "nearest_landslide_km": None,
            "landslide_exposure": 0,
            "reasons": ["No historical landslide locations evaluated."],
        }

    if nearest_distance <= 15:
        exposure = 22
        reason = f"Segment is within {nearest_distance:.1f} km of a validated historical landslide point."
    elif nearest_distance <= 40:
        exposure = 10
        reason = f"Segment is near historical landslide zones ({nearest_distance:.1f} km away)."
    else:
        exposure = 0
        reason = "No nearby historical landslide exposure identified."

    return {
        "historical_data_available": True,
        "nearest_landslide_km": round(nearest_distance, 3),
        "landslide_exposure": exposure,
        "reasons": [reason],
    }


def _road_adjustment(segment: dict[str, Any]) -> tuple[int, list[str], bool]:
    """Returns (road_and_slope_score, reasons, slope_available)."""
    score = 0
    reasons: list[str] = []

    road_class = str(segment.get("road_class") or "unknown").lower()
    class_risk_map = {
        "expressway": 5,
        "national_highway": 12,
        "major": 12,
        "primary": 12,
        "state_highway": 20,
        "secondary": 24,
        "collector": 28,
        "tertiary": 32,
        "local": 35,
        "residential": 35,
        "unclassified": 30,
        "unknown": 25,
    }
    road_score = class_risk_map.get(road_class, 25)
    score += road_score
    reasons.append(f"Road classification '{road_class}' carries baseline infrastructure risk.")

    raw_slope = segment.get("slope_deg", segment.get("slope"))
    slope = _as_float(raw_slope)
    slope_available = slope is not None

    if slope_available:
        if slope >= 15:
            score += 30
            reasons.append(f"Steep slope ({slope:.1f}°) elevates landslide and vehicle control risk.")
        elif slope >= 8:
            score += 18
            reasons.append(f"Elevated slope ({slope:.1f}°) increases risk.")
        elif slope >= 4:
            score += 8
            reasons.append(f"Moderate terrain slope ({slope:.1f}°).")
    else:
        reasons.append("Terrain slope is unavailable; the score excludes terrain risk.")

    surface = str(segment.get("surface") or "").lower()
    if surface and surface in {"gravel", "dirt", "mud", "unpaved", "earth"}:
        score += 15
        reasons.append(f"Road surface is {surface}, increasing traction failure and washout risk.")

    return score, reasons, slope_available


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


# ---------------------------------------------------------------------------
# Public Baseline Scorer for a Single Segment (Contract Aligned)
# ---------------------------------------------------------------------------

def score_segment_baseline(
    segment: dict[str, Any], context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Score a single segment using deterministic rules and hazard indices.

    Follows the backend contract:
    - score: integer 0-100
    - risk_level: "low" (0-33), "medium" (34-66), "high" (67-100)
    - factors: list of {name, contribution, detail}
    - data_quality: "complete", "partial", "stale", "unavailable"
    """
    context = context or {}
    sid = _normalize_segment_id(segment)
    factors: list[dict[str, Any]] = []

    # Vehicle sensitivity factor
    vehicle_type = str(context.get("vehicle_type", "truck")).lower()
    vehicle_multiplier = 1.2 if vehicle_type == "truck" else (1.0 if vehicle_type == "van" else 0.8)

    # 1. Slope & Terrain
    raw_slope = segment.get("slope_deg", segment.get("slope"))
    slope = _as_float(raw_slope)
    slope_available = slope is not None

    if not slope_available:
        slope_score = 0.0
        factors.append({
            "name": "terrain_unavailable",
            "contribution": 0.0,
            "detail": "Terrain slope is unavailable; the score excludes terrain risk.",
        })
    elif slope >= 8.0:
        slope_score = min(35.0, round(slope * 3.0))
        factors.append({
            "name": "steep_terrain",
            "contribution": float(slope_score),
            "detail": f"Terrain slope is {slope:.1f}%, elevating rollover and brake wear risk.",
        })
    elif slope >= 4.0:
        slope_score = round(slope * 2.0)
        factors.append({
            "name": "moderate_terrain",
            "contribution": float(slope_score),
            "detail": f"Terrain slope is {slope:.1f}%.",
        })
    else:
        slope_score = 0.0

    # 2. Road infrastructure & class
    road_class = str(segment.get("road_class", "secondary")).lower()
    class_risk_map = {
        "expressway": 5.0,
        "national_highway": 12.0,
        "major": 12.0,
        "primary": 12.0,
        "state_highway": 20.0,
        "secondary": 28.0,
        "collector": 28.0,
        "tertiary": 35.0,
        "local": 35.0,
        "residential": 35.0,
        "unknown": 25.0,
    }
    road_score = class_risk_map.get(road_class, 25.0)
    factors.append({
        "name": "road_infrastructure",
        "contribution": float(road_score),
        "detail": f"Road classification '{road_class}' carries baseline infrastructure risk.",
    })

    # Surface quality check
    surface = str(segment.get("surface") or "").lower()
    surface_score = 0.0
    if surface in {"gravel", "dirt", "mud", "unpaved", "earth"}:
        surface_score = 12.0
        factors.append({
            "name": "unpaved_surface",
            "contribution": float(surface_score),
            "detail": f"Road surface is {surface}, increasing traction failure and washout risk.",
        })

    # 3. Weather Evaluation & Freshness
    weather_match = _nearest_weather_for_segment(segment, context)
    weather_contrib = 0.0

    if not weather_match.get("weather_available", False):
        weather_status = weather_match.get("status")
        if weather_status == "future_only":
            detail = "Weather data could not be fetched; only future observations exist relative to departure time."
        elif weather_status == "missing_coordinates":
            detail = "Weather data could not be fetched; segment has no geographic coordinates."
        else:
            detail = "Weather data could not be fetched; score uses road and history factors only."
        factors.append({
            "name": "weather_unavailable",
            "contribution": 0.0,
            "detail": detail,
        })
    elif weather_match.get("stale", False):
        age_hours = weather_match.get("observation_age_hours") or 24.0
        weather_contrib = 8.0
        factors.append({
            "name": "stale_weather",
            "contribution": float(weather_contrib),
            "detail": f"Weather observation is {age_hours:.1f} hours old (>24h); weather uncertainty elevated.",
        })
    elif weather_match.get("distant", False):
        station_km = weather_match.get("nearest_station_km") or 50.0
        weather_contrib = 6.0
        factors.append({
            "name": "distant_weather_station",
            "contribution": float(weather_contrib),
            "detail": f"Nearest weather station is {station_km:.1f} km away (>50 km); localized mountain weather unverified.",
        })
    else:
        w_risk = weather_match.get("weather_risk") or {}
        w_score = w_risk.get("risk_score")
        if w_score is not None and w_score > 0:
            weather_contrib = float(w_score)
            if w_score >= 67:
                factors.append({
                    "name": "heavy_rainfall",
                    "contribution": float(weather_contrib),
                    "detail": "Localized precipitation increases slickness and landslide probability.",
                })
            elif w_score >= 34:
                factors.append({
                    "name": "moderate_rainfall",
                    "contribution": float(weather_contrib),
                    "detail": "Moderate precipitation elevates slickness and braking distances.",
                })
            else:
                factors.append({
                    "name": "light_rainfall",
                    "contribution": float(weather_contrib),
                    "detail": "Light rainfall detected in proximity.",
                })
        elif w_score is None:
            factors.append({
                "name": "weather_unavailable",
                "contribution": 0.0,
                "detail": "Weather data incomplete or invalid.",
            })

    # 4. Historical Disaster Exposure
    history_match = _historical_exposure_for_segment(segment)
    history_contrib = 0.0

    if not history_match.get("historical_data_available", False):
        factors.append({
            "name": "history_unavailable",
            "contribution": 0.0,
            "detail": "Historical disaster data is unavailable.",
        })
    else:
        dist_km = history_match.get("nearest_landslide_km")
        if dist_km is not None and dist_km <= 15.0:
            history_contrib = 22.0
            factors.append({
                "name": "landslide_history",
                "contribution": float(history_contrib),
                "detail": f"Segment is within {dist_km:.1f} km of a validated historical landslide point.",
            })
        elif dist_km is not None and dist_km <= 40.0:
            history_contrib = 10.0
            factors.append({
                "name": "past_disruptions",
                "contribution": float(history_contrib),
                "detail": f"Segment is near historical landslide zones ({dist_km:.1f} km away).",
            })
        else:
            history_contrib = 6.0

    # 5. Determine Data Quality
    coordinates_ok = _segment_coordinates(segment) is not None
    weather_ok = weather_match.get("weather_complete", False)
    weather_avail = weather_match.get("weather_available", False)
    history_ok = history_match.get("historical_data_available", False)

    if not coordinates_ok and not weather_avail:
        data_quality = "unavailable"
    elif weather_match.get("stale", False):
        data_quality = "stale"
    elif not weather_ok or not slope_available or not history_ok or weather_match.get("distant", False):
        data_quality = "partial"
    else:
        data_quality = "complete"

    # Compute Final Score
    raw_score = (
        slope_score + road_score + surface_score + weather_contrib + history_contrib
    ) * vehicle_multiplier
    final_score = int(min(max(round(raw_score), 0), 100))

    return {
        "score": final_score,
        "risk_level": _risk_level_lower(final_score),
        "factors": factors,
        "data_quality": data_quality,
        "risk_source": "baseline",
    }


# ---------------------------------------------------------------------------
# Model Adapter with Graceful Fallback
# ---------------------------------------------------------------------------

def _validate_experimental_model_artifact(payload: Any) -> Any:
    """Validate artifact structure, feature schema, provenance and acceptance evidence."""
    try:
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as error:
        raise RuntimeError("scikit-learn is unavailable for model inference.") from error

    if not isinstance(payload, dict) or set(payload) != {"pipeline", "metadata"}:
        raise RuntimeError("Experimental model artifact has an invalid payload structure.")
    pipeline = payload["pipeline"]
    metadata = payload["metadata"]
    if not isinstance(pipeline, Pipeline) or not isinstance(metadata, dict):
        raise RuntimeError("Experimental model artifact has an invalid pipeline or metadata.")
    if metadata.get("feature_columns") != list(WEATHER_FEATURE_COLUMNS):
        raise RuntimeError("Experimental model feature schema is incompatible.")
    if set(metadata.get("class_labels", [])) != set(MODEL_CLASS_LABELS):
        raise RuntimeError("Experimental model class-label metadata is incompatible.")
    if metadata.get("production_eligible") is not False:
        raise RuntimeError("Experimental model metadata must explicitly prohibit production use.")
    if metadata.get("task") != "weather-risk classification, not road-disruption prediction":
        raise RuntimeError("Experimental model task metadata is missing or incompatible.")

    provenance = metadata.get("label_provenance")
    if (
        not isinstance(provenance, dict)
        or provenance.get("type") != "synthetic_heuristic"
        or provenance.get("generation")
        != "calculate_weather_risk(features)['risk_level'] for every row"
        or provenance.get("per_row_marker") != "label_provenance"
    ):
        raise RuntimeError("Experimental model synthetic-label provenance is missing or invalid.")
    data_provenance = metadata.get("data_provenance")
    if (
        not isinstance(data_provenance, dict)
        or not data_provenance.get("source_path")
        or len(str(data_provenance.get("source_sha256", ""))) != 64
    ):
        raise RuntimeError("Experimental model data provenance is missing or invalid.")
    try:
        if int(metadata["random_seed"]) < 0:
            raise ValueError("random_seed must be non-negative")
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("Experimental model random-seed metadata is invalid.") from error

    if set(pipeline.named_steps) != {"imputer", "scaler", "classifier"}:
        raise RuntimeError("Experimental model preprocessing pipeline is incomplete.")
    if (
        not isinstance(pipeline.named_steps["imputer"], SimpleImputer)
        or not isinstance(pipeline.named_steps["scaler"], StandardScaler)
        or not isinstance(pipeline.named_steps["classifier"], LogisticRegression)
    ):
        raise RuntimeError("Experimental model preprocessing or estimator type is incompatible.")
    if tuple(getattr(pipeline, "feature_names_in_", ())) != WEATHER_FEATURE_COLUMNS:
        raise RuntimeError("Experimental model fitted feature schema is incompatible.")
    classifier = pipeline.named_steps["classifier"]
    if set(getattr(classifier, "classes_", ())) != set(MODEL_CLASS_LABELS):
        raise RuntimeError("Experimental model classifier classes are incompatible.")

    acceptance = metadata.get("acceptance_criteria")
    evaluation = metadata.get("evaluation")
    if not isinstance(acceptance, dict) or not isinstance(evaluation, dict):
        raise RuntimeError("Experimental model evaluation metadata is incomplete.")
    if any(acceptance.get(key) != value for key, value in MODEL_ACCEPTANCE_THRESHOLDS.items()):
        raise RuntimeError("Experimental model acceptance thresholds are incompatible.")
    test_counts = evaluation.get("test_class_distribution")
    metrics = evaluation.get("metrics")
    if not isinstance(test_counts, dict) or not isinstance(metrics, dict):
        raise RuntimeError("Experimental model evaluation results are incomplete.")
    model_metrics = metrics.get("logistic_regression")
    majority_metrics = metrics.get("majority_class_baseline")
    if not isinstance(model_metrics, dict) or not isinstance(majority_metrics, dict):
        raise RuntimeError("Experimental model comparison metrics are incomplete.")
    try:
        support_accepted = all(
            int(test_counts[label]) >= MODEL_ACCEPTANCE_THRESHOLDS["minimum_test_support_per_class"]
            for label in MODEL_CLASS_LABELS
        )
        macro_f1 = float(model_metrics["macro_f1"])
        accuracy = float(model_metrics["accuracy"])
        majority_macro_f1 = float(majority_metrics["macro_f1"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("Experimental model evaluation results are invalid.") from error
    derived_checks = {
        "test_support_adequate": support_accepted,
        "macro_f1_threshold_met": macro_f1 >= MODEL_ACCEPTANCE_THRESHOLDS["minimum_macro_f1"],
        "accuracy_threshold_met": accuracy >= MODEL_ACCEPTANCE_THRESHOLDS["minimum_accuracy"],
        "majority_baseline_improvement_met": (
            macro_f1 - majority_macro_f1
            >= MODEL_ACCEPTANCE_THRESHOLDS["minimum_macro_f1_improvement_over_majority"]
        ),
    }
    if any(acceptance.get(key) is not value for key, value in derived_checks.items()):
        raise RuntimeError("Experimental model acceptance metadata does not match its evaluation results.")
    if any(
        not math.isfinite(metric) or not 0.0 <= metric <= 1.0
        for metric in (macro_f1, accuracy, majority_macro_f1)
    ):
        raise RuntimeError("Experimental model evaluation metrics are outside valid ranges.")
    if not all(derived_checks.values()) or acceptance.get("experimental_criteria_met") is not True:
        raise RuntimeError("Experimental model failed the predefined evaluation acceptance criteria.")
    if acceptance.get("production_acceptance") is not False:
        raise RuntimeError("Synthetic-label artifacts cannot be marked production-accepted.")
    return pipeline


@lru_cache(maxsize=2)
def _load_experimental_weather_model(model_path: str) -> Any:
    path = Path(model_path)
    if not path.is_file():
        raise RuntimeError(f"Experimental weather-risk model artifact is missing: {path}")
    try:
        import joblib

        payload = joblib.load(path)
    except (OSError, EOFError, ValueError, ImportError, AttributeError, pickle.UnpicklingError) as error:
        raise RuntimeError(f"Experimental weather-risk model artifact could not be loaded: {error}") from error
    except Exception as error:
        raise RuntimeError(f"Experimental weather-risk model artifact is corrupt or incompatible: {error}") from error
    return _validate_experimental_model_artifact(payload)


def score_segment_model(
    segment: dict[str, Any], context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Score weather class experimentally; reject artifacts that fail recorded criteria.

    The model only imitates synthetic weather-risk labels and is never enabled by
    default. Callers must explicitly set ``risk_source="experimental_model"``.
    """
    context = context or {}
    if str(context.get("risk_source", "")).lower() != "experimental_model":
        raise RuntimeError("Experimental weather-risk inference requires explicit opt-in.")

    weather_match = _nearest_weather_for_segment(segment, context)
    if not weather_match.get("weather_complete", False):
        raise ValueError(
            "Experimental model requires complete, fresh, nearby weather features; "
            f"weather status is {weather_match.get('status', 'unknown')}."
        )
    weather_features = weather_match.get("weather_features")
    if not isinstance(weather_features, dict):
        raise ValueError("Experimental model weather features are unavailable.")

    try:
        from .risk_model_features import prepare_weather_features
    except ImportError:  # pragma: no cover - supports direct script imports
        from risk_model_features import prepare_weather_features

    features = prepare_weather_features(weather_features)
    pipeline = _load_experimental_weather_model(str(EXPERIMENTAL_MODEL_PATH.resolve()))
    prediction = str(pipeline.predict(features)[0]).upper()
    score_by_class = {"LOW": 16, "MEDIUM": 50, "HIGH": 83}
    if prediction not in score_by_class:
        raise RuntimeError(f"Experimental model returned an unsupported class: {prediction!r}")

    score_value = score_by_class[prediction]
    return {
        "score": score_value,
        "risk_level": _risk_level_lower(score_value),
        "factors": [{
            "name": "experimental_weather_classifier",
            "contribution": float(score_value),
            "detail": (
                f"Experimental weather class {prediction} from a classifier trained on "
                "synthetic rule-generated labels; not validated road-disruption prediction."
            ),
        }],
        "data_quality": "partial",
        "risk_source": "model",
        "experimental": True,
    }


# ---------------------------------------------------------------------------
# Backend Contract: Public score(segments, context)
# ---------------------------------------------------------------------------

def score(
    segments: Any, context: dict[str, Any] | None = None
) -> dict[str, dict[str, Any]]:
    """Primary Risk & ML interface specified in backend API contract (§4.2).

    Parameters:
        segments: List of segment dictionaries (or single segment/route).
        context: Context dictionary containing `vehicle_type`, `departure_time` (or `as_of`),
                 and optional `risk_source` ("baseline", "model", or the explicit
                 "experimental_model" opt-in).

    Returns:
        Dictionary mapping `segment_id` to:
        {
            "score": int,
            "risk_level": "low" | "medium" | "high",
            "factors": list[dict],
            "data_quality": "complete" | "partial" | "stale" | "unavailable",
            "risk_source": "baseline" | "model"
        }
    """
    context = context or {}
    segment_list = _coerce_segment_list(segments)
    desired_source = str(context.get("risk_source", "baseline")).lower()
    experimental_mode = desired_source == "experimental_model"

    results: dict[str, dict[str, Any]] = {}

    if desired_source in {"model", "experimental_model"}:
        try:
            for seg in segment_list:
                sid = _normalize_segment_id(seg)
                results[sid] = score_segment_model(
                    seg,
                    {**context, "risk_source": "experimental_model"} if experimental_mode else context,
                )
            if experimental_mode:
                logger.warning(
                    "Experimental synthetic-label weather model was explicitly requested; "
                    "results are not validated real-world risk predictions."
                )
            return results
        except Exception as e:
            logger.warning("Model scoring failed (%s); gracefully falling back to baseline rules.", e)
            results.clear()

    # Baseline scoring
    for seg in segment_list:
        sid = _normalize_segment_id(seg)
        results[sid] = score_segment_baseline(seg, context)

    return results


# ---------------------------------------------------------------------------
# Backward Compatibility: score_segments, score_route, score_routes
# ---------------------------------------------------------------------------

def score_segments(segments: Any, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Score a list of routing segments, preserving original segment_id and legacy fields."""
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

        road_score, road_reasons, slope_available = _road_adjustment(segment)
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
                    "slope_deg": segment.get("slope_deg", segment.get("slope")),
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
                "terrain_available": slope_available,
                "nearest_weather_station_km": weather_match.get("nearest_station_km"),
                "weather_time": weather_match.get("weather_time"),
                "observation_age_hours": weather_match.get("observation_age_hours"),
                "stale": weather_match.get("stale", False),
                "distant": weather_match.get("distant", False),
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
    """Score multiple route candidates."""
    context = context or {}
    return [score_route(route, context) for route in routes]


__all__ = [
    "score",
    "score_segment_baseline",
    "score_segment_model",
    "score_segments",
    "score_route",
    "score_routes",
]
