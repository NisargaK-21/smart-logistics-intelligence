import shutil
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.reports import FieldReport, FieldReportCreate
from backend.app.services.reporting_service import reporting_service

router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parents[3] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@router.post(
    "/upload",
    summary="Upload an incident photo",
)
async def upload_report_photo(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type {ext}. Supported formats: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    unique_filename = f"{uuid.uuid4().hex[:16]}{ext}"
    destination_path = UPLOAD_DIR / unique_filename

    with destination_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

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
