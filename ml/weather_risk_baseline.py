"""Weather risk baseline calculation module.

Calculates segment-level weather risk scores based on precipitation and wind thresholds.
Risk levels aligned with backend contract:
- LOW: 0-33
- MEDIUM: 34-66
- HIGH: 67-100
"""

import math

try:
    from .risk_model_features import WEATHER_FEATURE_COLUMNS
except ImportError:  # pragma: no cover - supports direct script imports
    from risk_model_features import WEATHER_FEATURE_COLUMNS


def calculate_weather_risk(weather):
    required = WEATHER_FEATURE_COLUMNS

    missing = [key for key in required if weather.get(key) is None]

    if missing:
        return {
            "risk_score": None,
            "risk_level": "UNKNOWN",
            "reasons": [f"Missing features: {', '.join(missing)}"],
        }

    try:
        values = {key: float(weather[key]) for key in required}
    except (TypeError, ValueError):
        return {
            "risk_score": None,
            "risk_level": "UNKNOWN",
            "reasons": ["Weather features must be numeric."],
        }

    if any(math.isnan(val) or math.isinf(val) for val in values.values()):
        return {
            "risk_score": None,
            "risk_level": "UNKNOWN",
            "reasons": ["Weather features cannot be NaN or infinite."],
        }

    if any(value < 0 for value in values.values()):
        return {
            "risk_score": None,
            "risk_level": "UNKNOWN",
            "reasons": ["Weather features cannot be negative."],
        }

    score = 0
    reasons = []

    if values["precipitation_mm"] >= 20:
        score += 20
        reasons.append("Heavy hourly rainfall")
    elif values["precipitation_mm"] >= 10:
        score += 10
        reasons.append("Elevated hourly rainfall")

    if values["precipitation_sum_3h_mm"] >= 50:
        score += 20
        reasons.append("High rainfall over 3 hours")
    elif values["precipitation_sum_3h_mm"] >= 25:
        score += 10
        reasons.append("Elevated rainfall over 3 hours")

    if values["precipitation_sum_6h_mm"] >= 80:
        score += 20
        reasons.append("High rainfall over 6 hours")
    elif values["precipitation_sum_6h_mm"] >= 40:
        score += 10
        reasons.append("Elevated rainfall over 6 hours")

    if values["precipitation_sum_24h_mm"] >= 150:
        score += 25
        reasons.append("Very high rainfall over 24 hours")
    elif values["precipitation_sum_24h_mm"] >= 75:
        score += 15
        reasons.append("Elevated rainfall over 24 hours")

    if values["wind_speed_kmh"] >= 60:
        score += 15
        reasons.append("Very high wind speed")
    elif values["wind_speed_kmh"] >= 40:
        score += 5
        reasons.append("Elevated wind speed")

    score = min(score, 100)

    # Risk level categorization aligned with backend contract:
    # LOW: 0-33, MEDIUM: 34-66, HIGH: 67-100
    if score >= 67:
        level = "HIGH"
    elif score >= 34:
        level = "MEDIUM"
    else:
        level = "LOW"

    if not reasons:
        reasons.append("No weather thresholds triggered")

    return {
        "risk_score": score,
        "risk_level": level,
        "reasons": reasons,
    }
