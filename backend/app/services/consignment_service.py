import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from backend.app.models import ConsignmentRecord, VehicleRecord
from backend.app.schemas.consignments import ConsignmentCreate, ConsignmentUpdate


class ConsignmentService:
    def list(
        self,
        session: Session,
        status: Optional[str] = None,
        commodity: Optional[str] = None,
        vehicle_id: Optional[str] = None,
    ) -> List[ConsignmentRecord]:
        stmt = select(ConsignmentRecord)
        if status:
            stmt = stmt.where(ConsignmentRecord.lifecycle_status == status)
        if commodity:
            stmt = stmt.where(ConsignmentRecord.commodity_type == commodity)
        if vehicle_id:
            stmt = stmt.where(ConsignmentRecord.assigned_vehicle_id == vehicle_id)
        stmt = stmt.order_by(ConsignmentRecord.created_at.desc())
        return list(session.scalars(stmt).all())

    def get(self, session: Session, shipment_id: str) -> Optional[ConsignmentRecord]:
        return session.get(ConsignmentRecord, shipment_id)

    def create(self, session: Session, payload: ConsignmentCreate) -> ConsignmentRecord:
        now = datetime.now(timezone.utc)
        shipment_id = payload.shipment_id or f"SHP-{uuid.uuid4().hex[:8].upper()}"

        # If vehicle assigned, inherit current telemetry coordinates
        current_lat = payload.current_lat
        current_lng = payload.current_lng
        route_id = payload.route_id

        if payload.assigned_vehicle_id:
            vehicle = session.get(VehicleRecord, payload.assigned_vehicle_id)
            if vehicle:
                if current_lat is None:
                    current_lat = vehicle.latitude
                if current_lng is None:
                    current_lng = vehicle.longitude
                if not route_id:
                    route_id = vehicle.route_id

        record = ConsignmentRecord(
            shipment_id=shipment_id,
            commodity_type=payload.commodity_type,
            quantity=payload.quantity,
            origin=payload.origin,
            destination=payload.destination,
            assigned_vehicle_id=payload.assigned_vehicle_id,
            route_id=route_id,
            lifecycle_status=payload.lifecycle_status,
            current_lat=current_lat,
            current_lng=current_lng,
            risk_score=payload.risk_score or 25,
            eta_minutes=payload.eta_minutes or 60.0,
            notes=payload.notes,
            created_at=now,
            updated_at=now,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    def update(
        self, session: Session, shipment_id: str, payload: ConsignmentUpdate
    ) -> Optional[ConsignmentRecord]:
        record = session.get(ConsignmentRecord, shipment_id)
        if not record:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(record, key, value)

        record.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(record)
        return record

    def sync_with_vehicle(
        self, session: Session, vehicle_id: str, lat: float, lng: float, new_status: Optional[str] = None
    ) -> None:
        """Called during simulation to update assigned consignments automatically."""
        stmt = select(ConsignmentRecord).where(ConsignmentRecord.assigned_vehicle_id == vehicle_id)
        consignments = list(session.scalars(stmt).all())
        now = datetime.now(timezone.utc)
        for c in consignments:
            c.current_lat = lat
            c.current_lng = lng
            if new_status:
                c.lifecycle_status = new_status
            c.updated_at = now
        if consignments:
            session.commit()

    def count(self, session: Session, status: Optional[str] = None) -> int:
        stmt = select(func.count()).select_from(ConsignmentRecord)
        if status:
            stmt = stmt.where(ConsignmentRecord.lifecycle_status == status)
        return session.scalar(stmt) or 0


consignment_service = ConsignmentService()
