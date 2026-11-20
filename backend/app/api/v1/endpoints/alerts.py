from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.alerts import (
    Alert,
    AlertCreate,
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
    session: Session = Depends(get_db),
):
    return alert_service.list_alerts(session, route_id=route_id)


@router.post(
    "",
    response_model=Alert,
    summary="Create a corridor alert",
)
def create_alert(alert_in: AlertCreate, session: Session = Depends(get_db)):
    return alert_service.create_alert(session, alert_in)


@router.post(
    "/subscribe",
    response_model=AlertSubscribeResponse,
    summary="Register email or webhook for alerts on a route",
)
def subscribe_to_alerts(
    sub_req: AlertSubscribeRequest, session: Session = Depends(get_db)
):
    return alert_service.subscribe(session, sub_req)
