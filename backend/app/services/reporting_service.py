import uuid
from datetime import datetime, timezone
from typing import List, Optional
from backend.app.schemas.common import Coordinates
from backend.app.schemas.reports import FieldReport, FieldReportCreate


class ReportingService:
    def __init__(self):
        self._reports: List[FieldReport] = []

    def create_report(self, report_in: FieldReportCreate) -> FieldReport:
        now_iso = datetime.now(timezone.utc).astimezone().isoformat()
        report_id = f"rep-{uuid.uuid4().hex[:6]}"
        new_report = FieldReport(
            report_id=report_id,
            category=report_in.category,
            severity=report_in.severity,
            location=report_in.location,
            description=report_in.description,
            photo_url=report_in.photo_url,
            reporter_name=report_in.reporter_name or "Field Official",
            created_at=now_iso,
        )
        self._reports.append(new_report)
        return new_report

    def list_reports(
        self, category: Optional[str] = None, severity: Optional[str] = None
    ) -> List[FieldReport]:
        results = self._reports
        if category:
            results = [r for r in results if r.category.lower() == category.lower()]
        if severity:
            results = [r for r in results if r.severity.lower() == severity.lower()]
        return results

    def count(self) -> int:
        return len(self._reports)


reporting_service = ReportingService()
