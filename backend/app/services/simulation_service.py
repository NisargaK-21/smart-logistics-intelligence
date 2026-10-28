import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Set
from fastapi import WebSocket
from backend.app.schemas.vehicles import (
    VehiclePosition,
    VehicleSimulateRequest,
    VehicleSimulateResponse,
)


class SimulationService:
    def __init__(self):
        self._active_connections: Set[WebSocket] = set()
        self._vehicles: Dict[str, VehiclePosition] = {
            "V001": VehiclePosition(
                vehicle_id="V001",
                lat=26.0500,
                lng=91.7500,
                speed_kmh=42.0,
                heading_deg=175.0,
                ts="2026-10-28T10:00:00+05:30",
            ),
            "V002": VehiclePosition(
                vehicle_id="V002",
                lat=25.8200,
                lng=91.8100,
                speed_kmh=48.0,
                heading_deg=160.0,
                ts="2026-10-28T10:00:00+05:30",
            ),
        }

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._active_connections.add(websocket)
        # Send current positions immediately
        for v in self._vehicles.values():
            await websocket.send_json(v.model_dump())

    def disconnect(self, websocket: WebSocket):
        self._active_connections.discard(websocket)

    async def broadcast(self, position: VehiclePosition):
        dead_connections = set()
        for conn in self._active_connections:
            try:
                await conn.send_json(position.model_dump())
            except Exception:
                dead_connections.add(conn)
        for dead in dead_connections:
            self._active_connections.discard(dead)

    def start_simulation(self, req: VehicleSimulateRequest) -> VehicleSimulateResponse:
        now_iso = datetime.now(timezone.utc).astimezone().isoformat()
        # Initial waypoint
        self._vehicles[req.vehicle_id] = VehiclePosition(
            vehicle_id=req.vehicle_id,
            lat=26.1445,
            lng=91.7362,
            speed_kmh=req.speed_kmh or 45.0,
            heading_deg=165.0,
            ts=now_iso,
        )
        return VehicleSimulateResponse(
            status="started",
            vehicle_id=req.vehicle_id,
            route_id=req.route_id,
            total_waypoints=15,
            message=f"Simulation for {req.vehicle_id} initiated along {req.route_id} at {req.speed_kmh or 45.0} km/h.",
        )

    def get_active_count(self) -> int:
        return len(self._vehicles)

    def get_positions(self) -> List[VehiclePosition]:
        return list(self._vehicles.values())


simulation_service = SimulationService()
