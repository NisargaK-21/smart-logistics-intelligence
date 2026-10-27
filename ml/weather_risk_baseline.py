
def calculate_weather_risk(weather):
    required = [
        "precipitation_mm",
        "precipitation_sum_3h_mm",
        "precipitation_sum_6h_mm",
        "precipitation_sum_24h_mm",
        "wind_speed_kmh",
    ]

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

    if score >= 70:
        level = "HIGH"
    elif score >= 35:
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
