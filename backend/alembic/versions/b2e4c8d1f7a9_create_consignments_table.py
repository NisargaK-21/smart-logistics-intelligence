"""Create consignments table safely.

Revision ID: b2e4c8d1f7a9
Revises: af003c501eed
Create Date: 2026-11-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b2e4c8d1f7a9"
down_revision: Union[str, Sequence[str], None] = "af003c501eed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
            sa.Column(
                "lifecycle_status",
                sa.String(length=32),
                nullable=False,
                server_default="Dispatched",
            ),
            sa.Column("current_lat", sa.Float(), nullable=True),
            sa.Column("current_lng", sa.Float(), nullable=True),
            sa.Column("risk_score", sa.Integer(), nullable=True),
            sa.Column("eta_minutes", sa.Float(), nullable=True),
            sa.Column("notes", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("shipment_id"),
        )

    _create_index_if_missing(
        "consignments", "ix_consignments_commodity_type", ["commodity_type"]
    )
    _create_index_if_missing(
        "consignments", "ix_consignments_lifecycle_status", ["lifecycle_status"]
    )
    _create_index_if_missing(
        "consignments", "ix_consignments_created_at", ["created_at"]
    )
    _create_index_if_missing(
        "consignments", "ix_consignments_updated_at", ["updated_at"]
    )
    _create_index_if_missing(
        "consignments", "ix_consignments_assigned_vehicle_id", ["assigned_vehicle_id"]
    )
    _create_index_if_missing(
        "consignments", "ix_consignments_route_id", ["route_id"]
    )


def downgrade() -> None:
    # consignments is also defined in af003c501eed for clean installs.
    # To prevent accidentally dropping a table created by the previous migration
    # during rollback, this downgrade is safely a no-op.
    pass
