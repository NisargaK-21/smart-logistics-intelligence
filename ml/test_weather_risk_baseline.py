
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


if __name__ == "__main__":
    test_normal_weather()
    test_heavy_rainfall()
    test_missing_weather()
    print("All baseline tests passed!")
