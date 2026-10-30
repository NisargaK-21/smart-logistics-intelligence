import uuid
from datetime import datetime, timezone
from typing import List, Optional
from backend.app.schemas.alerts import (
    Alert,
    AlertSubscribeRequest,
    AlertSubscribeResponse,
)
from backend.app.schemas.common import Coordinates


class AlertService:
    def __init__(self):
        self._alerts: List[Alert] = [
            Alert(
                alert_id="alt-101",
                route_id="route-1",
                vehicle_id="V001",
                severity="high",
                title="Approaching High-Risk Landslide Zone",
                message="Vehicle V001 is within 2.5 km of high-risk segment s-202 (Umsning sector).",
                location=Coordinates(lat=25.7500, lng=91.8500),
                distance_to_risk_km=2.1,
                created_at="2026-10-28T09:45:00+05:30",
            ),
            Alert(
                alert_id="alt-102",
                route_id="route-1",
                vehicle_id=None,
                severity="medium",
                title="Route Risk Elevation",
                message="Heavy rainfall has increased route-1 aggregate risk score past threshold (64).",
                location=None,
                distance_to_risk_km=None,
                created_at="2026-10-28T10:00:00+05:30",
            ),
        ]
        self._subscriptions: List[dict] = []

    def list_alerts(self, route_id: Optional[str] = None) -> List[Alert]:
        if route_id:
            return [a for a in self._alerts if a.route_id == route_id]
        return self._alerts

    def count(self) -> int:
        return len(self._alerts)

    def subscribe(self, sub_req: AlertSubscribeRequest) -> AlertSubscribeResponse:
        sub_id = f"sub-{uuid.uuid4().hex[:6]}"
        self._subscriptions.append({
            "id": sub_id,
            "email": sub_req.email,
            "route_id": sub_req.route_id,
            "threshold": sub_req.threshold_risk_score,
            "subscribed_at": datetime.now(timezone.utc).astimezone().isoformat(),
        })
        return AlertSubscribeResponse(
            status="subscribed",
            subscription_id=sub_id,
            email=sub_req.email,
            route_id=sub_req.route_id,
            threshold_risk_score=sub_req.threshold_risk_score or 65,
            message=f"Subscribed {sub_req.email} to alerts on {sub_req.route_id} when risk exceeds {sub_req.threshold_risk_score}.",
        )


alert_service = AlertService()
