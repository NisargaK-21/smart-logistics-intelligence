import pytest
from backend.app.services.seed_service import seed_initial_data
from backend.app.database import get_db


def test_list_consignments(client):
    # Seed initial test consignments into isolated test session
    # Create via API if empty
    create_payload = {
        "shipment_id": "SHP-SEED-01",
        "commodity_type": "Medicine",
        "quantity": "250 Boxes of Trauma & Antibiotic Kits",
        "origin": "Guwahati Central Medical Depot",
        "destination": "Shillong Civil Hospital",
        "assigned_vehicle_id": "V001",
        "route_id": "OSRM-260FB0617369-1",
        "lifecycle_status": "In Transit",
        "notes": "Urgent medical supplies",
    }
    client.post("/api/v1/consignments/", json=create_payload)

    response = client.get("/api/v1/consignments/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    item = data[0]
    assert "shipment_id" in item
    assert "commodity_type" in item
    assert "lifecycle_status" in item
    assert "origin" in item
    assert "destination" in item


def test_create_and_update_consignment(client):
    payload = {
        "shipment_id": "TEST-SHP-001",
        "commodity_type": "Medicine",
        "quantity": "100 Units Vaccine Coolers",
        "origin": "Guwahati Central Clinic",
        "destination": "Nongpoh PHC",
        "assigned_vehicle_id": "V001",
        "route_id": "route-1",
        "lifecycle_status": "Dispatched",
        "notes": "Urgent cold chain",
    }
    create_res = client.post("/api/v1/consignments/", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["shipment_id"] == "TEST-SHP-001"
    assert created_data["commodity_type"] == "Medicine"
    assert created_data["lifecycle_status"] == "Dispatched"

    # Patch lifecycle status
    update_res = client.patch(
        "/api/v1/consignments/TEST-SHP-001",
        json={"lifecycle_status": "In Transit", "notes": "En route via NH-6"},
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["lifecycle_status"] == "In Transit"
    assert updated_data["notes"] == "En route via NH-6"


def test_filter_consignments_by_commodity(client):
    payload = {
        "shipment_id": "TEST-SHP-MED",
        "commodity_type": "Medicine",
        "quantity": "50 Boxes",
        "origin": "Depot",
        "destination": "Hospital",
    }
    client.post("/api/v1/consignments/", json=payload)
    response = client.get("/api/v1/consignments/?commodity=Medicine")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    for item in data:
        assert item["commodity_type"] == "Medicine"
