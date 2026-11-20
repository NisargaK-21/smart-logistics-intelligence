from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, upgrade_database
from backend.app.models import (
    AlertSubscriptionRecord,
    FieldReportRecord,
    VehicleRecord,
)
from backend.app.schemas.alerts import AlertCreate, AlertSubscribeRequest
from backend.app.schemas.common import Coordinates
from backend.app.schemas.reports import FieldReportCreate
from backend.app.schemas.vehicles import VehicleSimulateRequest
from backend.app.services.alert_service import alert_service
from backend.app.services.reporting_service import reporting_service
from backend.app.services.simulation_service import simulation_service


def test_reports_alerts_subscriptions_and_vehicles_survive_database_restart(tmp_path):
    database_path = tmp_path / "persistence.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    upgrade_database(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        report = reporting_service.create_report(
            session,
            FieldReportCreate(
                category="landslide",
                severity="high",
                location=Coordinates(lat=25.88, lng=91.79),
                description="Road blocked by a landslide.",
                reporter_name="Inspector Das",
            ),
        )
        alert = alert_service.create_alert(
            session,
            AlertCreate(
                route_id="route-1",
                threshold=70,
                severity="high",
                title="High route risk",
                message="Risk score exceeded the configured threshold.",
            ),
        )
        subscription = alert_service.subscribe(
            session,
            AlertSubscribeRequest(
                email="operator@example.com",
                route_id="route-1",
                threshold_risk_score=0,
            ),
        )
        simulation_service.start_simulation(
            session,
            VehicleSimulateRequest(
                vehicle_id="V-PERSIST-1",
                route_id="route-1",
                vehicle_type="van",
                speed_kmh=50,
            ),
        )

    engine.dispose()
    restarted_engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    upgrade_database(restarted_engine)
    restarted_session_factory = sessionmaker(
        bind=restarted_engine, expire_on_commit=False
    )

    with restarted_session_factory() as session:
        reports = reporting_service.list_reports(session)
        alerts = alert_service.list_alerts(session, route_id="route-1")
        positions = simulation_service.get_positions(session)
        subscription_record = session.scalar(
            select(AlertSubscriptionRecord).where(
                AlertSubscriptionRecord.subscription_id == subscription.subscription_id
            )
        )
        vehicle_record = session.get(VehicleRecord, "V-PERSIST-1")

        assert [item.report_id for item in reports] == [report.report_id]
        assert [item.alert_id for item in alerts] == [alert.alert_id]
        assert alerts[0].threshold == 70
        assert [item.vehicle_id for item in positions] == ["V-PERSIST-1"]
        assert positions[0].speed_kmh == 50
        assert subscription_record is not None
        assert subscription_record.threshold == 0
        assert vehicle_record is not None
        assert vehicle_record.vehicle_type == "van"
        assert vehicle_record.status == "active"

    restarted_engine.dispose()


def test_migration_adopts_existing_schema_without_losing_reports(tmp_path):
    database_path = tmp_path / "existing.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        record = FieldReportRecord(
            report_id="rep-existing",
            category="road_blockage",
            severity="high",
            latitude=26.1,
            longitude=91.8,
            description="Existing report must remain available.",
            reporter_name="Field Officer",
            created_at=datetime.now(timezone.utc),
        )
        session.add(record)
        session.commit()

    engine.dispose()
    migrated_engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    upgrade_database(migrated_engine)
    migrated_session_factory = sessionmaker(
        bind=migrated_engine, expire_on_commit=False
    )

    with migrated_session_factory() as session:
        reports = reporting_service.list_reports(session)
        assert [report.report_id for report in reports] == ["rep-existing"]

    migrated_engine.dispose()
