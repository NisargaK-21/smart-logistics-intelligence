from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.reports import FieldReport, FieldReportCreate
from backend.app.services.reporting_service import reporting_service

router = APIRouter()


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
