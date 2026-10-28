from backend.app.core.config import settings


def test_health_ok(client):
    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True
    settings.WEATHER_AVAILABLE = True

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["modules"]["gis"] == "ok"
    assert data["modules"]["risk"] == "ok"
    assert data["modules"]["weather"] == "ok"


def test_health_weather_degraded(client):
    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True
    settings.WEATHER_AVAILABLE = False

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["modules"]["gis"] == "ok"
    assert data["modules"]["risk"] == "ok"
    assert data["modules"]["weather"] == "degraded"


def test_health_gis_down(client):
    settings.GIS_SERVICE_ENABLED = False
    settings.RISK_SERVICE_ENABLED = True
    settings.WEATHER_AVAILABLE = True

    response = client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert data["error"]["details"]["module"] == "gis"

    # Reset
    settings.GIS_SERVICE_ENABLED = True


def test_health_risk_down(client):
    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = False
    settings.WEATHER_AVAILABLE = True

    response = client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert data["error"]["details"]["module"] == "risk"

    # Reset
    settings.RISK_SERVICE_ENABLED = True
