from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from backend.app.api.v1.api import api_router
from backend.app.core.config import settings
from backend.app.core.errors import register_exception_handlers
from backend.app.database import SessionLocal, get_db, upgrade_database
from backend.app.services.seed_service import seed_initial_data
from backend.app.services.simulation_service import simulation_service

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    upgrade_database()
    with SessionLocal() as session:
        seed_initial_data(session)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
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

# Mount static files directory for uploaded photos
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)



@app.websocket("/ws/vehicles")
async def websocket_vehicles(websocket: WebSocket, session: Session = Depends(get_db)):
    """
    WebSocket endpoint streaming real-time simulated vehicle positions:
    {vehicle_id, lat, lng, speed_kmh, heading_deg, ts}
    """
    await simulation_service.connect(websocket, session)
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