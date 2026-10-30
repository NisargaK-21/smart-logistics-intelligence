def test_get_coverage_metadata(client):
    response = client.get("/api/v1/meta/coverage")
    assert response.status_code == 200
    data = response.json()
    assert "bbox" in data
    assert len(data["bbox"]) == 4
    min_lng, min_lat, max_lng, max_lat = data["bbox"]
    assert min_lng < max_lng
    assert min_lat < max_lat
    assert "vehicle_types" in data
    assert "truck" in data["vehicle_types"]
    assert "van" in data["vehicle_types"]
    assert "car" in data["vehicle_types"]
