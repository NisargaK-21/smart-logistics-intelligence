from fastapi import APIRouter
from backend.app.schemas.dashboard import DashboardSummary, RouteRiskSummary
from backend.app.services.alert_service import alert_service
from backend.app.services.reporting_service import reporting_service
from backend.app.services.simulation_service import simulation_service

router = APIRouter()


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Centralized dashboard summary metrics",
)
def get_dashboard_summary():
    return DashboardSummary(
        active_alerts_count=alert_service.count(),
        recent_reports_count=reporting_service.count(),
        active_vehicles_count=simulation_service.get_active_count(),
        overall_system_status="operational",
        risk_by_route=[
            RouteRiskSummary(
                route_id="route-1",
                risk_score=64,
                risk_level="medium",
                active_vehicles=1,
            ),
            RouteRiskSummary(
                route_id="route-2",
                risk_score=38,
                risk_level="medium",
                active_vehicles=1,
            ),
        ],
        high_risk_zones_count=2,
    )
