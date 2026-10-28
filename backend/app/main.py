from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.v1.api import api_router
from backend.app.core.config import settings
from backend.app.core.errors import register_exception_handlers
from backend.app.services.simulation_service import simulation_service

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register custom exception handlers for uniform error format
register_exception_handlers(app)

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.websocket("/ws/vehicles")
async def websocket_vehicles(websocket: WebSocket):
    """
    WebSocket endpoint streaming real-time simulated vehicle positions:
    {vehicle_id, lat, lng, speed_kmh, heading_deg, ts}
    """
    await simulation_service.connect(websocket)
    try:
        while True:
            # Keep socket open and receive heartbeat/ping from client
            await websocket.receive_text()
    except WebSocketDisconnect:
        simulation_service.disconnect(websocket)
    except Exception:
        simulation_service.disconnect(websocket)


@app.get("/")
def root():
    return {
        "message": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "api_v1": settings.API_V1_STR,
    }


@app.get("/health")
def legacy_health():
    """Simple ping endpoint for infrastructure load balancers."""
    return {"status": "healthy"}