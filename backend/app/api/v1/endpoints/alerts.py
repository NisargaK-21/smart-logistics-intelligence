from typing import List, Optional
from fastapi import APIRouter, Query
from backend.app.schemas.alerts import (
    Alert,
    AlertSubscribeRequest,
    AlertSubscribeResponse,
)
from backend.app.services.alert_service import alert_service

router = APIRouter()


@router.get(
    "",
    response_model=List[Alert],
    summary="List active risk and proximity alerts",
)
def list_alerts(
    route_id: Optional[str] = Query(None, description="Filter alerts by route_id"),
):
    return alert_service.list_alerts(route_id=route_id)


@router.post(
    "/subscribe",
    response_model=AlertSubscribeResponse,
    summary="Register email or webhook for alerts on a route",
)
def subscribe_to_alerts(sub_req: AlertSubscribeRequest):
    return alert_service.subscribe(sub_req)
