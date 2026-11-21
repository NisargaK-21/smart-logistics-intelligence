"""Create operational data tables.

Revision ID: af003c501eed
Revises:
Create Date: 2026-11-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "af003c501eed"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _validate_existing_table(name: str, expected_columns: set[str]) -> None:
    inspector = sa.inspect(op.get_bind())
    actual_columns = {column["name"] for column in inspector.get_columns(name)}
    missing_columns = expected_columns - actual_columns
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise RuntimeError(
            f"Existing table {name!r} is missing required columns: {missing}"
        )


def _create_index_if_missing(
    table_name: str, index_name: str, columns: list[str]
) -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name not in indexes:
        op.create_index(index_name, table_name, columns, unique=False)


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())

    if "alert_subscriptions" not in existing_tables:
        op.create_table(
            "alert_subscriptions",
            sa.Column("subscription_id", sa.String(length=32), nullable=False),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("route_id", sa.String(length=128), nullable=False),
            sa.Column("threshold", sa.Integer(), nullable=False),
            sa.Column("subscribed_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("subscription_id"),
        )
    else:
        _validate_existing_table(
            "alert_subscriptions",
            {"subscription_id", "email", "route_id", "threshold", "subscribed_at"},
        )
    _create_index_if_missing(
        "alert_subscriptions", "ix_alert_subscriptions_route_id", ["route_id"]
    )
    _create_index_if_missing(
        "alert_subscriptions",
        "ix_alert_subscriptions_route_email",
        ["route_id", "email"],
    )

    if "alerts" not in existing_tables:
        op.create_table(
            "alerts",
            sa.Column("alert_id", sa.String(length=32), nullable=False),
            sa.Column("route_id", sa.String(length=128), nullable=True),
            sa.Column("threshold", sa.Integer(), nullable=True),
            sa.Column("severity", sa.String(length=32), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("message", sa.String(), nullable=False),
            sa.Column("vehicle_id", sa.String(length=128), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("distance_to_risk_km", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("alert_id"),
        )
    else:
        _validate_existing_table(
            "alerts",
            {
                "alert_id",
                "route_id",
                "threshold",
                "severity",
                "title",
                "message",
                "vehicle_id",
                "latitude",
                "longitude",
                "distance_to_risk_km",
                "created_at",
            },
        )
    _create_index_if_missing("alerts", "ix_alerts_created_at", ["created_at"])
    _create_index_if_missing("alerts", "ix_alerts_route_id", ["route_id"])
    _create_index_if_missing("alerts", "ix_alerts_severity", ["severity"])

    if "field_reports" not in existing_tables:
        op.create_table(
            "field_reports",
            sa.Column("report_id", sa.String(length=32), nullable=False),
            sa.Column("category", sa.String(length=100), nullable=False),
            sa.Column("severity", sa.String(length=32), nullable=False),
            sa.Column("latitude", sa.Float(), nullable=False),
            sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("description", sa.String(), nullable=False),
            sa.Column("photo_url", sa.String(), nullable=True),
            sa.Column("reporter_name", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("report_id"),
        )
    else:
        _validate_existing_table(
            "field_reports",
            {
                "report_id",
                "category",
                "severity",
                "latitude",
                "longitude",
                "description",
                "photo_url",
                "reporter_name",
                "created_at",
            },
        )
    _create_index_if_missing(
        "field_reports", "ix_field_reports_category", ["category"]
    )
    _create_index_if_missing(
        "field_reports", "ix_field_reports_created_at", ["created_at"]
    )
    _create_index_if_missing(
        "field_reports", "ix_field_reports_severity", ["severity"]
    )

    if "vehicles" not in existing_tables:
        op.create_table(
            "vehicles",
            sa.Column("vehicle_id", sa.String(length=128), nullable=False),
            sa.Column("vehicle_type", sa.String(length=32), nullable=False),
            sa.Column("route_id", sa.String(length=128), nullable=False),
            sa.Column("latitude", sa.Float(), nullable=False),
            sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("speed_kmh", sa.Float(), nullable=False),
            sa.Column("heading_deg", sa.Float(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("vehicle_id"),
        )
    else:
        _validate_existing_table(
            "vehicles",
            {
                "vehicle_id",
                "vehicle_type",
                "route_id",
                "latitude",
                "longitude",
                "status",
                "speed_kmh",
                "heading_deg",
                "updated_at",
            },
        )
    _create_index_if_missing("vehicles", "ix_vehicles_status", ["status"])
    _create_index_if_missing("vehicles", "ix_vehicles_updated_at", ["updated_at"])

    if "consignments" not in existing_tables:
        op.create_table(
            "consignments",
            sa.Column("shipment_id", sa.String(length=64), nullable=False),
            sa.Column("commodity_type", sa.String(length=64), nullable=False),
            sa.Column("quantity", sa.String(length=128), nullable=False),
            sa.Column("origin", sa.String(length=255), nullable=False),
            sa.Column("destination", sa.String(length=255), nullable=False),
            sa.Column("assigned_vehicle_id", sa.String(length=128), nullable=True),
            sa.Column("route_id", sa.String(length=128), nullable=True),
            sa.Column("lifecycle_status", sa.String(length=32), nullable=False, server_default="Dispatched"),
            sa.Column("current_lat", sa.Float(), nullable=True),
            sa.Column("current_lng", sa.Float(), nullable=True),
            sa.Column("risk_score", sa.Integer(), nullable=True),
            sa.Column("eta_minutes", sa.Float(), nullable=True),
            sa.Column("notes", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("shipment_id"),
        )
    _create_index_if_missing("consignments", "ix_consignments_commodity_type", ["commodity_type"])
    _create_index_if_missing("consignments", "ix_consignments_lifecycle_status", ["lifecycle_status"])
    _create_index_if_missing("consignments", "ix_consignments_created_at", ["created_at"])
    _create_index_if_missing("consignments", "ix_consignments_updated_at", ["updated_at"])
    _create_index_if_missing("consignments", "ix_consignments_assigned_vehicle_id", ["assigned_vehicle_id"])
    _create_index_if_missing("consignments", "ix_consignments_route_id", ["route_id"])


def downgrade() -> None:
    op.drop_index(
        "ix_alert_subscriptions_route_email",
        table_name="alert_subscriptions",
    )
    op.drop_index("ix_vehicles_updated_at", table_name="vehicles")
    op.drop_index("ix_vehicles_status", table_name="vehicles")
    op.drop_table("vehicles")

    op.drop_index("ix_field_reports_severity", table_name="field_reports")
    op.drop_index("ix_field_reports_created_at", table_name="field_reports")
    op.drop_index("ix_field_reports_category", table_name="field_reports")
    op.drop_table("field_reports")

    op.drop_index("ix_alerts_severity", table_name="alerts")
    op.drop_index("ix_alerts_route_id", table_name="alerts")
    op.drop_index("ix_alerts_created_at", table_name="alerts")
    op.drop_table("alerts")

    op.drop_index("ix_alert_subscriptions_route_id", table_name="alert_subscriptions")
    op.drop_table("alert_subscriptions")
