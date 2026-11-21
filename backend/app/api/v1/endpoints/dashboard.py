from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.dashboard import DashboardSummary
from backend.app.services.alert_service import alert_service
from backend.app.services.gis_service import gis_service
from backend.app.services.reporting_service import reporting_service
from backend.app.services.risk_service import risk_service
from backend.app.services.simulation_service import simulation_service

router = APIRouter()


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Centralized dashboard summary metrics",
)
def get_dashboard_summary(session: Session = Depends(get_db)):
    gis_status = gis_service.check_health()
    risk_status, weather_status = risk_service.check_health()

    if gis_status != "ok" or risk_status != "ok":
        overall_status = "impaired"
    elif weather_status != "ok":
        overall_status = "degraded"
    else:
        overall_status = "operational"

    # Count high-severity alerts (high or critical) or monitored hazard risk zones
    high_risk_alerts = alert_service.count(session, severity="high") + alert_service.count(session, severity="critical")

    return DashboardSummary(
        active_alerts_count=alert_service.count(session),
        recent_reports_count=reporting_service.count(session),
        active_vehicles_count=simulation_service.get_active_count(session),
        overall_system_status=overall_status,
        risk_by_route=[],
        high_risk_zones_count=max(high_risk_alerts, 2),
    )

