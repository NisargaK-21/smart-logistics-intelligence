def test_vehicles_simulate_and_active(client):
    req_payload = {
        "vehicle_id": "V-TEST-99",
        "route_id": "route-1",
        "speed_kmh": 50.0,
    }
    response = client.post("/api/v1/vehicles/simulate", json=req_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert data["vehicle_id"] == "V-TEST-99"

    # List active vehicles
    list_resp = client.get("/api/v1/vehicles/active")
    assert list_resp.status_code == 200
    v_list = list_resp.json()
    assert any(v["vehicle_id"] == "V-TEST-99" for v in v_list)


def test_field_reports_crud(client):
    report_data = {
        "category": "landslide",
        "severity": "critical",
        "location": {"lat": 25.8800, "lng": 91.7900},
        "description": "Rockfall on secondary hill route sector 4.",
        "reporter_name": "Inspector Das",
    }
    create_resp = client.post("/api/v1/reports", json=report_data)
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert "report_id" in created
    assert created["category"] == "landslide"
    assert created["severity"] == "critical"

    # List reports with filter
    list_resp = client.get("/api/v1/reports?category=landslide")
    assert list_resp.status_code == 200
    reports = list_resp.json()
    assert any(r["report_id"] == created["report_id"] for r in reports)


def test_alerts_list_and_subscribe(client):
    # List active alerts
    list_resp = client.get("/api/v1/alerts")
    assert list_resp.status_code == 200
    alerts = list_resp.json()
    assert len(alerts) >= 1

    # Subscribe to alerts on a route
    sub_payload = {
        "email": "logistics.manager@fmcg.in",
        "route_id": "route-1",
        "threshold_risk_score": 70,
    }
    sub_resp = client.post("/api/v1/alerts/subscribe", json=sub_payload)
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()
    assert sub_data["status"] == "subscribed"
    assert sub_data["email"] == "logistics.manager@fmcg.in"


def test_dashboard_summary(client):
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "active_alerts_count" in data
    assert "recent_reports_count" in data
    assert "active_vehicles_count" in data
    assert "overall_system_status" in data
    assert "risk_by_route" in data
    assert len(data["risk_by_route"]) >= 1


def test_websocket_vehicles_streaming():
    import asyncio
    from backend.app.main import app

    async def run_ws():
        messages = []
        incoming = asyncio.Queue()
        await incoming.put({"type": "websocket.connect"})

        async def receive():
            return await incoming.get()

        async def send(msg):
            messages.append(msg)

        scope = {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "scheme": "ws",
            "path": "/ws/vehicles",
            "raw_path": b"/ws/vehicles",
            "query_string": b"",
            "headers": [(b"host", b"localhost")],
            "subprotocols": [],
            "client": ("127.0.0.1", 12345),
            "server": ("127.0.0.1", 8000),
            "app": app,
        }
        task = asyncio.create_task(app(scope, receive, send))
        await asyncio.sleep(0.05)
        await incoming.put({"type": "websocket.disconnect", "code": 1000})
        await asyncio.sleep(0.05)
        task.cancel()
        return messages

    messages = asyncio.run(run_ws())
    assert len(messages) >= 2
    assert messages[0]["type"] == "websocket.accept"
    assert any("vehicle_id" in m.get("text", "") for m in messages[1:])

