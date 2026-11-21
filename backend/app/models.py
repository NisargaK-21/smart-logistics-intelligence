from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class FieldReportRecord(Base):
    __tablename__ = "field_reports"

    report_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    severity: Mapped[str] = mapped_column(String(32), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(String)
    photo_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reporter_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AlertRecord(Base):
    __tablename__ = "alerts"

    alert_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    route_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    threshold: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    severity: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(String)
    vehicle_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    distance_to_risk_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AlertSubscriptionRecord(Base):
    __tablename__ = "alert_subscriptions"

    subscription_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    email: Mapped[str] = mapped_column(String(320))
    route_id: Mapped[str] = mapped_column(String(128), index=True)
    threshold: Mapped[int] = mapped_column(Integer)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


Index(
    "ix_alert_subscriptions_route_email",
    AlertSubscriptionRecord.route_id,
    AlertSubscriptionRecord.email,
)


class VehicleRecord(Base):
    __tablename__ = "vehicles"

    vehicle_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    vehicle_type: Mapped[str] = mapped_column(String(32))
    route_id: Mapped[str] = mapped_column(String(128))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), index=True)
    speed_kmh: Mapped[float] = mapped_column(Float)
    heading_deg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ConsignmentRecord(Base):
    __tablename__ = "consignments"

    shipment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    commodity_type: Mapped[str] = mapped_column(String(64), index=True)  # Food Supplies, Medicine, Fuel, Emergency Kits
    quantity: Mapped[str] = mapped_column(String(128))  # e.g., "500 Bags", "1200 Units"
    origin: Mapped[str] = mapped_column(String(255))
    destination: Mapped[str] = mapped_column(String(255))
    assigned_vehicle_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    route_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    lifecycle_status: Mapped[str] = mapped_column(String(32), default="Dispatched", index=True)  # Dispatched, In Transit, Delayed due to Risk, Delivered
    current_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    current_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    eta_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
