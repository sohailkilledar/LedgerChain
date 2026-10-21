"""add product batches and auditable inventory shipments

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATES = "'PREPARED', 'DISPATCHED', 'IN_TRANSIT', 'RECEIVED', 'REJECTED'"


def upgrade() -> None:
    op.create_table(
        "inventory_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("batch_code", sa.String(80), nullable=False),
        sa.Column("manufactured_on", sa.Date(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("notes", sa.String(240), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("manufactured_on IS NULL OR expires_on IS NULL OR manufactured_on <= expires_on", name="ck_inventory_batches_batch_date_order"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "product_id", "batch_code", name="uq_inventory_batch_product_code"),
    )
    op.create_index("ix_inventory_batches_organization_created", "inventory_batches", ["organization_id", "created_at"])

    with op.batch_alter_table("inventory_stocks") as batch_op:
        batch_op.drop_constraint("uq_inventory_stock_location", type_="unique")
        batch_op.add_column(sa.Column("batch_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key("fk_inventory_stocks_batch_id_inventory_batches", "inventory_batches", ["batch_id"], ["id"], ondelete="RESTRICT")
    with op.batch_alter_table("inventory_movements") as batch_op:
        batch_op.add_column(sa.Column("batch_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key("fk_inventory_movements_batch_id_inventory_batches", "inventory_batches", ["batch_id"], ["id"], ondelete="RESTRICT")

    predicate_null = sa.text("batch_id IS NULL")
    predicate_set = sa.text("batch_id IS NOT NULL")
    op.create_index("uq_inventory_stocks_unbatched_location", "inventory_stocks", ["organization_id", "product_id", "location"], unique=True, sqlite_where=predicate_null, postgresql_where=predicate_null)
    op.create_index("uq_inventory_stocks_batched_location", "inventory_stocks", ["organization_id", "product_id", "location", "batch_id"], unique=True, sqlite_where=predicate_set, postgresql_where=predicate_set)
    op.create_index("ix_inventory_stocks_batch", "inventory_stocks", ["batch_id"])

    op.create_table(
        "inventory_shipments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sender_organization_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_organization_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("dispatcher_user_id", sa.Uuid(), nullable=True),
        sa.Column("receiver_user_id", sa.Uuid(), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("source_location", sa.String(120), nullable=False),
        sa.Column("destination_location", sa.String(120), nullable=False),
        sa.Column("status", sa.String(16), server_default="PREPARED", nullable=False),
        sa.Column("note", sa.String(240), nullable=True),
        sa.Column("rejection_reason", sa.String(240), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("in_transit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("quantity > 0", name="ck_inventory_shipments_quantity_positive"),
        sa.CheckConstraint(f"status IN ({_STATES})", name="ck_inventory_shipments_status"),
        sa.CheckConstraint("sender_organization_id != recipient_organization_id", name="ck_inventory_shipments_organizations_differ"),
        sa.ForeignKeyConstraint(["sender_organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recipient_organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["batch_id"], ["inventory_batches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["dispatcher_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["receiver_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sender_organization_id", "idempotency_key", name="uq_inventory_shipment_idempotency"),
    )
    op.create_index("ix_inventory_shipments_sender_status", "inventory_shipments", ["sender_organization_id", "status", "created_at"])
    op.create_index("ix_inventory_shipments_recipient_status", "inventory_shipments", ["recipient_organization_id", "status", "created_at"])

    op.create_table(
        "inventory_shipment_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shipment_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_organization_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(16), nullable=True),
        sa.Column("to_status", sa.String(16), nullable=False),
        sa.Column("detail", sa.String(240), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("sequence_number > 0", name="ck_inventory_shipment_events_sequence_positive"),
        sa.CheckConstraint(f"from_status IS NULL OR from_status IN ({_STATES})", name="ck_inventory_shipment_events_from_status"),
        sa.CheckConstraint(f"to_status IN ({_STATES})", name="ck_inventory_shipment_events_to_status"),
        sa.ForeignKeyConstraint(["shipment_id"], ["inventory_shipments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shipment_id", "sequence_number", name="uq_inventory_shipment_event_sequence"),
        sa.UniqueConstraint("shipment_id", "idempotency_key", name="uq_inventory_shipment_event_idempotency"),
    )
    op.create_index("ix_inventory_shipment_events_shipment_sequence", "inventory_shipment_events", ["shipment_id", "sequence_number"])

    if op.get_context().dialect.name == "sqlite":
        op.execute("CREATE TRIGGER ck_inventory_shipment_events_no_update BEFORE UPDATE ON inventory_shipment_events BEGIN SELECT RAISE(ABORT, 'inventory shipment history is append-only'); END")
        op.execute("CREATE TRIGGER ck_inventory_shipment_events_no_delete BEFORE DELETE ON inventory_shipment_events BEGIN SELECT RAISE(ABORT, 'inventory shipment history is append-only'); END")
    else:
        op.execute("CREATE FUNCTION inventory_shipment_event_guard() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'inventory shipment history is append-only' USING ERRCODE = '23514'; END; $$")
        op.execute("CREATE TRIGGER ck_inventory_shipment_events_immutable BEFORE UPDATE OR DELETE ON inventory_shipment_events FOR EACH ROW EXECUTE FUNCTION inventory_shipment_event_guard()")


def downgrade() -> None:
    if op.get_context().dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS ck_inventory_shipment_events_no_update")
        op.execute("DROP TRIGGER IF EXISTS ck_inventory_shipment_events_no_delete")
    else:
        op.execute("DROP TRIGGER IF EXISTS ck_inventory_shipment_events_immutable ON inventory_shipment_events")
        op.execute("DROP FUNCTION IF EXISTS inventory_shipment_event_guard()")
    op.drop_index("ix_inventory_shipment_events_shipment_sequence", table_name="inventory_shipment_events")
    op.drop_table("inventory_shipment_events")
    op.drop_index("ix_inventory_shipments_recipient_status", table_name="inventory_shipments")
    op.drop_index("ix_inventory_shipments_sender_status", table_name="inventory_shipments")
    op.drop_table("inventory_shipments")
    op.drop_index("ix_inventory_stocks_batch", table_name="inventory_stocks")
    op.drop_index("uq_inventory_stocks_batched_location", table_name="inventory_stocks")
    op.drop_index("uq_inventory_stocks_unbatched_location", table_name="inventory_stocks")
    with op.batch_alter_table("inventory_movements") as batch_op:
        batch_op.drop_constraint("fk_inventory_movements_batch_id_inventory_batches", type_="foreignkey")
        batch_op.drop_column("batch_id")
    with op.batch_alter_table("inventory_stocks") as batch_op:
        batch_op.drop_constraint("fk_inventory_stocks_batch_id_inventory_batches", type_="foreignkey")
        batch_op.drop_column("batch_id")
        batch_op.create_unique_constraint("uq_inventory_stock_location", ["organization_id", "product_id", "location"])
    op.drop_index("ix_inventory_batches_organization_created", table_name="inventory_batches")
    op.drop_table("inventory_batches")
