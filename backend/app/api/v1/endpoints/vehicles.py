from fastapi import APIRouter
from backend.app.schemas.vehicles import (
    VehiclePosition,
    VehicleSimulateRequest,
    VehicleSimulateResponse,
)
from backend.app.services.simulation_service import simulation_service

router = APIRouter()


@router.post(
    "/simulate",
    response_model=VehicleSimulateResponse,
    summary="Start a simulated vehicle trip along a planned route",
)
def simulate_vehicle(request: VehicleSimulateRequest):
    return simulation_service.start_simulation(request)


@router.get(
    "/active",
    response_model=list[VehiclePosition],
    summary="Get current positions of all active vehicles",
)
def get_active_vehicles():
    return simulation_service.get_positions()
