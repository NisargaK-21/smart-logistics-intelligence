import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session

from backend.app.models import AlertRecord, ConsignmentRecord, FieldReportRecord, VehicleRecord

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

        # 4. Seed Initial Essential Commodities Consignments if empty
        consignment_count = session.query(ConsignmentRecord).count()
        if consignment_count == 0:
            now = datetime.now(timezone.utc)
            initial_consignments = [
                ConsignmentRecord(
                    shipment_id="SHP-MED-8491",
                    commodity_type="Medicine",
                    quantity="250 Boxes of Trauma & Antibiotic Kits",
                    origin="Guwahati Central Medical Depot",
                    destination="Shillong Civil Hospital",
                    assigned_vehicle_id="V001",
                    route_id="OSRM-260FB0617369-1",
                    lifecycle_status="In Transit",
                    current_lat=26.050,
                    current_lng=91.750,
                    risk_score=28,
                    eta_minutes=45.0,
                    notes="Temperature-sensitive cargo, prioritized detour around active landslides.",
                    created_at=now,
                    updated_at=now,
                ),
                ConsignmentRecord(
                    shipment_id="SHP-FOOD-2940",
                    commodity_type="Food Supplies",
                    quantity="500 Sacks of Rice & Fortified Pulses",
                    origin="FCI Dispur Grain Silo",
                    destination="Nongpoh Relief Staging Center",
                    assigned_vehicle_id="V002",
                    route_id="OSRM-260FB0617369-1",
                    lifecycle_status="In Transit",
                    current_lat=25.820,
                    current_lng=91.810,
                    risk_score=35,
                    eta_minutes=70.0,
                    notes="Monitored for water damage and flood detours.",
                    created_at=now,
                    updated_at=now,
                ),
                ConsignmentRecord(
                    shipment_id="SHP-FUEL-1029",
                    commodity_type="Fuel",
                    quantity="12,000 Liters High-Speed Diesel",
                    origin="IOCL Betkuchi Terminal",
                    destination="Mawlai Emergency Power Generator Station",
                    assigned_vehicle_id="V004",
                    route_id="OSRM-260FB0617369-1",
                    lifecycle_status="Delayed due to Risk",
                    current_lat=25.680,
                    current_lng=91.890,
                    risk_score=68,
                    eta_minutes=115.0,
                    notes="Halted briefly near Nongpoh sector due to rockfall warning.",
                    created_at=now,
                    updated_at=now,
                ),
                ConsignmentRecord(
                    shipment_id="SHP-KIT-5510",
                    commodity_type="Emergency Kits",
                    quantity="150 Inflatable Boats & Water Purifiers",
                    origin="NDRF 1st Bn Base Patgaon",
                    destination="Byrnihat Flood Evacuation Camp",
                    assigned_vehicle_id="V003",
                    route_id="OSRM-260FB0617369-1",
                    lifecycle_status="Delivered",
                    current_lat=26.1445,
                    current_lng=91.7362,
                    risk_score=15,
                    eta_minutes=0.0,
                    notes="Delivered successfully to camp commander.",
                    created_at=now,
                    updated_at=now,
                ),
            ]
            for c in initial_consignments:
                session.add(c)
            session.commit()
            logger.info("Seeded initial essential commodity consignments.")
    except Exception as exc:
        logger.warning(f"Error seeding initial data: {exc}")
        session.rollback()
