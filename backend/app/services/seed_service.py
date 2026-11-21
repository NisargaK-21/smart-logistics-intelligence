import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session

from backend.app.models import AlertRecord, FieldReportRecord, VehicleRecord

logger = logging.getLogger(__name__)

RAW_REPORTS_CSV = Path(__file__).resolve().parents[3] / "ml" / "data" / "raw" / "field_reports" / "field_reports.csv"


def seed_initial_data(session: Session) -> None:
    """
    Populates initial real dataset records into the database if empty,
    ensuring the system is dynamic, reflects ground-truth datasets, and
    does not start with empty counters.
    """
    try:
        # 1. Seed Field Reports from empirical raw dataset
        report_count = session.query(FieldReportRecord).count()
        if report_count == 0 and RAW_REPORTS_CSV.exists():
            with open(RAW_REPORTS_CSV, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    created_at = datetime.now(timezone.utc)
                    if row.get("timestamp"):
                        try:
                            created_at = datetime.fromisoformat(row["timestamp"]).replace(tzinfo=timezone.utc)
                        except Exception:
                            pass

                    record = FieldReportRecord(
                        report_id=row.get("report_id") or f"rep-{row.get('latitude')}",
                        category=row.get("incident_type") or "landslide",
                        severity=row.get("severity") or "medium",
                        latitude=float(row.get("latitude", 26.1445)),
                        longitude=float(row.get("longitude", 91.7362)),
                        description=row.get("description") or "Observed road obstacle",
                        photo_url=row.get("image_path") or None,
                        reporter_name=row.get("reported_by") or "Field Official",
                        created_at=created_at,
                    )
                    session.add(record)
            session.commit()
            logger.info("Seeded initial field reports from raw dataset.")

        # 2. Seed Initial Corridor Alerts if empty
        alert_count = session.query(AlertRecord).count()
        if alert_count == 0:
            initial_alerts = [
                AlertRecord(
                    alert_id="alt-nh6-001",
                    route_id="OSRM-260FB0617369-1",
                    threshold=65,
                    severity="high",
                    title="Flash Flood / Water Accumulation Alert",
                    message="Severe water accumulation observed along NH-6 culvert km 42; reduced speed advised.",
                    vehicle_id="V001",
                    latitude=25.820,
                    longitude=91.810,
                    distance_to_risk_km=1.2,
                    created_at=datetime.now(timezone.utc),
                ),
                AlertRecord(
                    alert_id="alt-nh6-002",
                    route_id="OSRM-260FB0617369-1",
                    threshold=70,
                    severity="critical",
                    title="Active Landslide Warning",
                    message="Loose soil and debris movement on uphill slope near Byrnihat corridor.",
                    vehicle_id="V002",
                    latitude=25.980,
                    longitude=91.800,
                    distance_to_risk_km=3.5,
                    created_at=datetime.now(timezone.utc),
                ),
                AlertRecord(
                    alert_id="alt-nh6-003",
                    route_id="OSRM-260FB0617369-1",
                    threshold=50,
                    severity="medium",
                    title="Heavy Precipitation & Fog Advisory",
                    message="Dense mist and heavy rain reducing visibility below 50m along Nongpoh ascent.",
                    vehicle_id=None,
                    latitude=25.900,
                    longitude=91.880,
                    distance_to_risk_km=0.8,
                    created_at=datetime.now(timezone.utc),
                ),
            ]
            for alert in initial_alerts:
                session.add(alert)
            session.commit()
            logger.info("Seeded initial corridor alerts.")

        # 3. Seed Initial Active Simulated Vehicles if empty
        vehicle_count = session.query(VehicleRecord).count()
        if vehicle_count == 0:
            now = datetime.now(timezone.utc)
            initial_vehicles = [
                VehicleRecord(
                    vehicle_id="V001",
                    vehicle_type="truck",
                    route_id="OSRM-260FB0617369-1",
                    latitude=26.050,
                    longitude=91.750,
                    status="active",
                    speed_kmh=42.0,
                    heading_deg=175.0,
                    updated_at=now,
                ),
                VehicleRecord(
                    vehicle_id="V002",
                    vehicle_type="van",
                    route_id="OSRM-260FB0617369-1",
                    latitude=25.820,
                    longitude=91.810,
                    status="active",
                    speed_kmh=48.0,
                    heading_deg=160.0,
                    updated_at=now,
                ),
                VehicleRecord(
                    vehicle_id="V003",
                    vehicle_type="car",
                    route_id="OSRM-260FB0617369-1",
                    latitude=26.1445,
                    longitude=91.7362,
                    status="active",
                    speed_kmh=35.0,
                    heading_deg=145.0,
                    updated_at=now,
                ),
                VehicleRecord(
                    vehicle_id="V004",
                    vehicle_type="truck",
                    route_id="OSRM-260FB0617369-1",
                    latitude=25.680,
                    longitude=91.890,
                    status="active",
                    speed_kmh=50.0,
                    heading_deg=170.0,
                    updated_at=now,
                ),
            ]
            for v in initial_vehicles:
                session.add(v)
            session.commit()
            logger.info("Seeded initial active vehicles.")
    except Exception as exc:
        logger.warning(f"Error seeding initial data: {exc}")
        session.rollback()
