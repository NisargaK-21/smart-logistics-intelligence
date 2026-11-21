from datetime import datetime, timezone
from typing import List, Set

from fastapi import WebSocket
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import VehicleRecord
from backend.app.schemas.vehicles import (
    VehiclePosition,
    VehicleSimulateRequest,
    VehicleSimulateResponse,
)


class SimulationService:
    def __init__(self):
        self._active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, session: Session):
        await websocket.accept()
        self._active_connections.add(websocket)
        for position in self.get_positions(session):
            await websocket.send_json(position.model_dump())

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

    def start_simulation(
        self, session: Session, req: VehicleSimulateRequest
    ) -> VehicleSimulateResponse:
        now = datetime.now(timezone.utc)
        record = session.get(VehicleRecord, req.vehicle_id)
        if record is None:
            record = VehicleRecord(
                vehicle_id=req.vehicle_id,
                vehicle_type=req.vehicle_type,
                route_id=req.route_id,
                latitude=26.1445,
                longitude=91.7362,
                status="active",
                speed_kmh=req.speed_kmh if req.speed_kmh is not None else 45.0,
                heading_deg=165.0,
                updated_at=now,
            )
            session.add(record)
        else:
            record.vehicle_type = req.vehicle_type
            record.route_id = req.route_id
            record.status = "active"
            record.speed_kmh = req.speed_kmh if req.speed_kmh is not None else 45.0
            record.updated_at = now
        session.commit()
        session.refresh(record)
        speed = req.speed_kmh if req.speed_kmh is not None else 45.0
        # Automatically update any consignments assigned to this vehicle to "In Transit"
        try:
            from backend.app.services.consignment_service import consignment_service
            consignment_service.sync_with_vehicle(
                session=session,
                vehicle_id=req.vehicle_id,
                lat=record.latitude,
                lng=record.longitude,
                new_status="In Transit",
            )
        except Exception:
            pass

        return VehicleSimulateResponse(
            status="started",
            vehicle_id=req.vehicle_id,
            route_id=req.route_id,
            total_waypoints=15,
            message=f"Simulation for {req.vehicle_id} initiated along {req.route_id} at {speed} km/h.",
        )

    def get_active_count(self, session: Session) -> int:
        return (
            session.scalar(
                select(func.count())
                .select_from(VehicleRecord)
                .where(VehicleRecord.status == "active")
            )
            or 0
        )

    def get_positions(self, session: Session) -> List[VehiclePosition]:
        records = session.scalars(
            select(VehicleRecord)
            .where(VehicleRecord.status == "active")
            .order_by(VehicleRecord.updated_at.desc())
        )
        return [
            VehiclePosition(
                vehicle_id=record.vehicle_id,
                lat=record.latitude,
                lng=record.longitude,
                speed_kmh=record.speed_kmh,
                heading_deg=record.heading_deg,
                ts=self._timestamp(record.updated_at),
            )
            for record in records
        ]

    @staticmethod
    def _timestamp(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()


simulation_service = SimulationService()
