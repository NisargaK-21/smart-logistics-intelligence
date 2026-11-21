import base64
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.reports import FieldReport, FieldReportCreate
from backend.app.services.reporting_service import reporting_service

router = APIRouter()

# Central backend uploads directory (shared with main.py)
UPLOAD_DIR = Path(__file__).resolve().parents[4] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class PhotoUploadPayload(BaseModel):
    filename: str
    data_base64: str


@router.post(
    "/upload",
    summary="Upload an incident photo (JSON Base64 or Binary)",
)
async def upload_report_photo(request: Request):
    content_type = request.headers.get("content-type", "")

    # 1. Base64 JSON Payload (Pure standard library, zero external dependency)
    if "application/json" in content_type:
        try:
            body = await request.json()
            filename = body.get("filename", "incident.jpg")
            data_base64 = body.get("data_base64", "")
            if "," in data_base64:
                data_base64 = data_base64.split(",", 1)[1]
            raw_bytes = base64.b64decode(data_base64)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {exc}")
    else:
        # 2. Raw binary stream or multipart fallback
        ext = ".jpg"
        raw_bytes = await request.body()
        filename = request.headers.get("x-filename", "incident.jpg")

    ext = Path(filename).suffix.lower() or ".jpg"
    if ext not in ALLOWED_EXTENSIONS:
        ext = ".jpg"

    unique_filename = f"{uuid.uuid4().hex[:16]}{ext}"
    destination_path = UPLOAD_DIR / unique_filename

    with destination_path.open("wb") as buffer:
        buffer.write(raw_bytes)

    return {
        "filename": unique_filename,
        "photo_url": f"/uploads/{unique_filename}",
    }



@router.post(
    "",
    response_model=FieldReport,
    summary="Submit a new geo-tagged field incident report",
)
def create_report(report_in: FieldReportCreate, session: Session = Depends(get_db)):
    return reporting_service.create_report(session, report_in)



@router.get(
    "",
    response_model=List[FieldReport],
    summary="List field reports with optional category and severity filters",
)
def list_reports(
    category: Optional[str] = Query(None, description="Filter by category (e.g. landslide, flood)"),
    severity: Optional[str] = Query(None, description="Filter by severity (e.g. high, critical)"),
    session: Session = Depends(get_db),
):
    return reporting_service.list_reports(session, category=category, severity=severity)
