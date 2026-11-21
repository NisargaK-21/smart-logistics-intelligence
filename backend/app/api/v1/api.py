from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    alerts,
    consignments,
    dashboard,
    health,
    meta,
    places,
    reports,
    routes,
    vehicles,
    weather,
)

api_router = APIRouter()

# Sprint Core Endpoints
api_router.include_router(routes.router, prefix="/routes", tags=["routes"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(meta.router, prefix="/meta", tags=["metadata"])
api_router.include_router(places.router, prefix="/places", tags=["places"])
api_router.include_router(weather.router, prefix="/weather", tags=["weather"])

# Extended Endpoints (Vehicle Simulation, Field Reports, Alerts, Consignments, Dashboard)
api_router.include_router(vehicles.router, prefix="/vehicles", tags=["vehicles"])
api_router.include_router(consignments.router, prefix="/consignments", tags=["consignments"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
