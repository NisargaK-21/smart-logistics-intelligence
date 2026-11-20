import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import FieldReportRecord
from backend.app.schemas.common import Coordinates
from backend.app.schemas.reports import FieldReport, FieldReportCreate


class ReportingService:
    def create_report(self, session: Session, report_in: FieldReportCreate) -> FieldReport:
        record = FieldReportRecord(
            report_id=f"rep-{uuid.uuid4().hex[:12]}",
            category=report_in.category,
            severity=report_in.severity,
            latitude=report_in.location.lat,
            longitude=report_in.location.lng,
            description=report_in.description,
            photo_url=report_in.photo_url,
            reporter_name=report_in.reporter_name or "Field Official",
            created_at=datetime.now(timezone.utc),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return self._to_schema(record)

    def list_reports(
        self,
        session: Session,
        category: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[FieldReport]:
        statement = select(FieldReportRecord)
        if category:
            statement = statement.where(
                func.lower(FieldReportRecord.category) == category.lower()
            )
        if severity:
            statement = statement.where(
                func.lower(FieldReportRecord.severity) == severity.lower()
            )
        statement = statement.order_by(FieldReportRecord.created_at.desc())
        return [self._to_schema(record) for record in session.scalars(statement)]

    def count(self, session: Session) -> int:
        return session.scalar(select(func.count()).select_from(FieldReportRecord)) or 0

    @staticmethod
    def _to_schema(record: FieldReportRecord) -> FieldReport:
        created_at = record.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return FieldReport(
            report_id=record.report_id,
            category=record.category,
            severity=record.severity,
            location=Coordinates(lat=record.latitude, lng=record.longitude),
            description=record.description,
            photo_url=record.photo_url,
            reporter_name=record.reporter_name,
            created_at=created_at.isoformat(),
        )


reporting_service = ReportingService()
