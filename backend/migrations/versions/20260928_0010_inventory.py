"""add organization-scoped inventory and immutable movement history

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inventory_stocks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("location", sa.String(length=120), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=3), server_default="0", nullable=False),
        sa.Column("low_stock_threshold", sa.Numeric(precision=18, scale=3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_inventory_stocks_quantity_non_negative"),
        sa.CheckConstraint("low_stock_threshold IS NULL OR low_stock_threshold >= 0", name="ck_inventory_stocks_threshold_non_negative"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "product_id", "location", name="uq_inventory_stock_location"),
    )
    op.create_index("ix_inventory_stocks_organization_updated", "inventory_stocks", ["organization_id", "updated_at"])
    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("movement_type", sa.String(length=16), nullable=False),
        sa.Column("source_location", sa.String(length=120), nullable=True),
        sa.Column("destination_location", sa.String(length=120), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=18, scale=3), nullable=False),
        sa.Column("adjustment_delta", sa.Numeric(precision=18, scale=3), nullable=True),
        sa.Column("reason", sa.String(length=240), nullable=True),
        sa.Column("source_quantity_before", sa.Numeric(precision=18, scale=3), nullable=True),
        sa.Column("source_quantity_after", sa.Numeric(precision=18, scale=3), nullable=True),
        sa.Column("destination_quantity_before", sa.Numeric(precision=18, scale=3), nullable=True),
        sa.Column("destination_quantity_after", sa.Numeric(precision=18, scale=3), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("movement_type IN ('stock_in', 'stock_out', 'movement', 'adjustment')", name="ck_inventory_movements_movement_type"),
        sa.CheckConstraint("quantity > 0", name="ck_inventory_movements_quantity_positive"),
        sa.CheckConstraint("adjustment_delta IS NULL OR adjustment_delta != 0", name="ck_inventory_movements_adjustment_delta_nonzero"),
        sa.CheckConstraint("source_location IS NOT NULL OR destination_location IS NOT NULL", name="ck_inventory_movements_location_required"),
        sa.CheckConstraint("source_quantity_before IS NULL OR source_quantity_before >= 0", name="ck_inventory_movements_source_before_non_negative"),
        sa.CheckConstraint("source_quantity_after IS NULL OR source_quantity_after >= 0", name="ck_inventory_movements_source_after_non_negative"),
        sa.CheckConstraint("destination_quantity_before IS NULL OR destination_quantity_before >= 0", name="ck_inventory_movements_destination_before_non_negative"),
        sa.CheckConstraint("destination_quantity_after IS NULL OR destination_quantity_after >= 0", name="ck_inventory_movements_destination_after_non_negative"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_inventory_movement_idempotency"),
    )
    op.create_index("ix_inventory_movements_organization_created", "inventory_movements", ["organization_id", "created_at"])
    op.create_index("ix_inventory_movements_product_created", "inventory_movements", ["product_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_inventory_movements_product_created", table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_organization_created", table_name="inventory_movements")
    op.drop_table("inventory_movements")
    op.drop_index("ix_inventory_stocks_organization_updated", table_name="inventory_stocks")
    op.drop_table("inventory_stocks")
