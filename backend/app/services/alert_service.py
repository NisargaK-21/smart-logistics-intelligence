import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import AlertRecord, AlertSubscriptionRecord
from backend.app.schemas.alerts import (
    Alert,
    AlertCreate,
    AlertSubscribeRequest,
    AlertSubscribeResponse,
)
from backend.app.schemas.common import Coordinates


class AlertService:
    def create_alert(self, session: Session, alert_in: AlertCreate) -> Alert:
        record = AlertRecord(
            alert_id=f"alt-{uuid.uuid4().hex[:12]}",
            route_id=alert_in.route_id,
            threshold=alert_in.threshold,
            severity=alert_in.severity,
            title=alert_in.title,
            message=alert_in.message,
            vehicle_id=alert_in.vehicle_id,
            latitude=alert_in.location.lat if alert_in.location else None,
            longitude=alert_in.location.lng if alert_in.location else None,
            distance_to_risk_km=alert_in.distance_to_risk_km,
            created_at=datetime.now(timezone.utc),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return self._to_schema(record)

    def list_alerts(self, session: Session, route_id: Optional[str] = None) -> List[Alert]:
        statement = select(AlertRecord)
        if route_id:
            statement = statement.where(AlertRecord.route_id == route_id)
        statement = statement.order_by(AlertRecord.created_at.desc())
        return [self._to_schema(record) for record in session.scalars(statement)]

    def count(self, session: Session, severity: Optional[str] = None) -> int:
        statement = select(func.count()).select_from(AlertRecord)
        if severity:
            statement = statement.where(func.lower(AlertRecord.severity) == severity.lower())
        return session.scalar(statement) or 0

    def subscribe(
        self, session: Session, sub_req: AlertSubscribeRequest
    ) -> AlertSubscribeResponse:
        threshold = (
            sub_req.threshold_risk_score
            if sub_req.threshold_risk_score is not None
            else 65
        )
        subscription_id = f"sub-{uuid.uuid4().hex[:12]}"
        session.add(
            AlertSubscriptionRecord(
                subscription_id=subscription_id,
                email=sub_req.email,
                route_id=sub_req.route_id,
                threshold=threshold,
                subscribed_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
        return AlertSubscribeResponse(
            status="subscribed",
            subscription_id=subscription_id,
            email=sub_req.email,
            route_id=sub_req.route_id,
            threshold_risk_score=threshold,
            message=f"Subscribed {sub_req.email} to alerts on {sub_req.route_id} when risk exceeds {threshold}.",
        )

    @staticmethod
    def _to_schema(record: AlertRecord) -> Alert:
        created_at = record.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        location = None
        if record.latitude is not None and record.longitude is not None:
            location = Coordinates(lat=record.latitude, lng=record.longitude)
        return Alert(
            alert_id=record.alert_id,
            route_id=record.route_id,
            threshold=record.threshold,
            vehicle_id=record.vehicle_id,
            severity=record.severity,
            title=record.title,
            message=record.message,
            location=location,
            distance_to_risk_km=record.distance_to_risk_km,
            created_at=created_at.isoformat(),
        )


alert_service = AlertService()
