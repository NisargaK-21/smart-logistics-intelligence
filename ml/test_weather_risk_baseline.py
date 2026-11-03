import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from weather_risk_baseline import calculate_weather_risk


def test_normal_weather():
    weather = {
        "precipitation_mm": 0,
        "precipitation_sum_3h_mm": 0,
        "precipitation_sum_6h_mm": 0,
        "precipitation_sum_24h_mm": 0,
        "wind_speed_kmh": 10,
    }
    result = calculate_weather_risk(weather)
    assert result["risk_level"] == "LOW"
    assert result["risk_score"] == 0


def test_heavy_rainfall():
    weather = {
        "precipitation_mm": 25,
        "precipitation_sum_3h_mm": 60,
        "precipitation_sum_6h_mm": 100,
        "precipitation_sum_24h_mm": 180,
        "wind_speed_kmh": 20,
    }
    result = calculate_weather_risk(weather)
    assert result["risk_level"] == "HIGH"
    assert result["risk_score"] == 85


def test_missing_weather():
    result = calculate_weather_risk({"precipitation_mm": 5})
    assert result["risk_level"] == "UNKNOWN"
    assert result["risk_score"] is None


def test_negative_weather_rejected():
    weather = {
        "precipitation_mm": -5,
        "precipitation_sum_3h_mm": 0,
        "precipitation_sum_6h_mm": 0,
        "precipitation_sum_24h_mm": 0,
        "wind_speed_kmh": 10,
    }
    result = calculate_weather_risk(weather)
    assert result["risk_score"] is None
    assert result["risk_level"] == "UNKNOWN"
    assert "cannot be negative" in result["reasons"][0]


def test_nan_weather_rejected():
    weather = {
        "precipitation_mm": float("nan"),
        "precipitation_sum_3h_mm": 0,
        "precipitation_sum_6h_mm": 0,
        "precipitation_sum_24h_mm": 0,
        "wind_speed_kmh": 10,
    }
    result = calculate_weather_risk(weather)
    assert result["risk_score"] is None
    assert result["risk_level"] == "UNKNOWN"
    assert "NaN or infinite" in result["reasons"][0]


def test_boundary_thresholds_aligned_with_backend_contract():
    # Test LOW upper boundary (score 30 <= 33)
    low_weather = {
        "precipitation_mm": 10,  # +10
        "precipitation_sum_3h_mm": 25,  # +10
        "precipitation_sum_6h_mm": 40,  # +10
        "precipitation_sum_24h_mm": 0,
        "wind_speed_kmh": 0,
    }
    res_low = calculate_weather_risk(low_weather)
    assert res_low["risk_score"] == 30
    assert res_low["risk_level"] == "LOW"

    # Test MEDIUM lower boundary (score 35 >= 34)
    med_weather = {
        "precipitation_mm": 10,  # +10
        "precipitation_sum_3h_mm": 25,  # +10
        "precipitation_sum_6h_mm": 0,
        "precipitation_sum_24h_mm": 75,  # +15
        "wind_speed_kmh": 0,
    }
    res_med = calculate_weather_risk(med_weather)
    assert res_med["risk_score"] == 35
    assert res_med["risk_level"] == "MEDIUM"

    # Test HIGH lower boundary (score 70 >= 67)
    high_weather = {
        "precipitation_mm": 20,  # +20
        "precipitation_sum_3h_mm": 50,  # +20
        "precipitation_sum_6h_mm": 0,
        "precipitation_sum_24h_mm": 150,  # +25
        "wind_speed_kmh": 40,  # +5
    }
    res_high = calculate_weather_risk(high_weather)
    assert res_high["risk_score"] == 70
    assert res_high["risk_level"] == "HIGH"


if __name__ == "__main__":
    test_normal_weather()
    test_heavy_rainfall()
    test_missing_weather()
    test_negative_weather_rejected()
    test_nan_weather_rejected()
    test_boundary_thresholds_aligned_with_backend_contract()
    print("All baseline tests passed!")
