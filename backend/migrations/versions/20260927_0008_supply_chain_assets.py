"""add products, assets, ownership and immutable provenance

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=3), nullable=True),
        sa.Column("unit", sa.String(length=24), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'discontinued')", name="ck_products_status"),
        sa.CheckConstraint("quantity IS NULL OR quantity >= 0", name="ck_products_quantity_non_negative"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "sku", name="uq_products_organization_sku"),
    )
    op.create_index("ix_products_organization_created", "products", ["organization_id", "created_at"])

    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("asset_identifier", sa.String(length=96), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("current_owner_organization_id", sa.Uuid(), nullable=False),
        sa.Column("current_custodian_organization_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'retired')", name="ck_assets_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["current_owner_organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["current_custodian_organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "asset_identifier", name="uq_assets_organization_identifier"),
    )
    op.create_index("ix_assets_owner_created", "assets", ["current_owner_organization_id", "created_at"])
    op.create_index("ix_assets_custodian", "assets", ["current_custodian_organization_id"])
    op.create_index("ix_assets_product_id", "assets", ["product_id"])

    op.create_table(
        "asset_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_organization_id", sa.Uuid(), nullable=False),
        sa.Column("previous_state", sa.JSON(), nullable=True),
        sa.Column("resulting_state", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('REGISTERED', 'TRANSFERRED', 'CUSTODY_CHANGED', 'RETIRED', 'PROVENANCE_RECORDED')",
            name="ck_asset_events_event_type",
        ),
        sa.CheckConstraint("sequence_number > 0", name="ck_asset_events_sequence_positive"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "sequence_number", name="uq_asset_events_asset_sequence"),
        sa.UniqueConstraint("asset_id", "actor_organization_id", "idempotency_key", name="uq_asset_events_idempotency"),
    )
    op.create_index("ix_asset_events_asset_sequence", "asset_events", ["asset_id", "sequence_number"])
    op.create_index("ix_asset_events_actor_created", "asset_events", ["actor_organization_id", "created_at"])

    op.create_table(
        "asset_ownerships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["event_id"], ["asset_events.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_asset_ownerships_event"),
    )
    op.create_index("ix_asset_ownerships_asset_created", "asset_ownerships", ["asset_id", "created_at"])
    op.create_index("ix_asset_ownerships_organization", "asset_ownerships", ["organization_id", "created_at"])

    with op.batch_alter_table("blockchain_records") as batch_op:
        batch_op.alter_column("ledger_transaction_id", existing_type=sa.Uuid(), nullable=True)
        batch_op.add_column(sa.Column("asset_event_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_blockchain_records_asset_event_id_asset_events", "asset_events", ["asset_event_id"], ["id"], ondelete="RESTRICT"
        )
        batch_op.create_unique_constraint("uq_blockchain_records_asset_event_id", ["asset_event_id"])
        batch_op.create_check_constraint(
            "record_reference",
            "(ledger_transaction_id IS NOT NULL AND asset_event_id IS NULL) OR "
            "(ledger_transaction_id IS NULL AND asset_event_id IS NOT NULL)",
        )

    _create_append_only_triggers()


def _create_append_only_triggers() -> None:
    if op.get_context().dialect.name == "sqlite":
        for table in ("asset_events", "asset_ownerships"):
            op.execute(
                f"CREATE TRIGGER ck_{table}_no_update BEFORE UPDATE ON {table} BEGIN "
                f"SELECT RAISE(ABORT, '{table} are append-only'); END"
            )
            op.execute(
                f"CREATE TRIGGER ck_{table}_no_delete BEFORE DELETE ON {table} BEGIN "
                f"SELECT RAISE(ABORT, '{table} are append-only'); END"
            )
        return
    op.execute(
        "CREATE FUNCTION asset_history_guard() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN RAISE EXCEPTION 'asset history is append-only' USING ERRCODE = '23514'; END; $$"
    )
    for table in ("asset_events", "asset_ownerships"):
        op.execute(
            f"CREATE TRIGGER ck_{table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION asset_history_guard()"
        )


def downgrade() -> None:
    if not op.get_context().as_sql:
        anchored = op.get_bind().execute(sa.text("SELECT count(*) FROM blockchain_records WHERE asset_event_id IS NOT NULL")).scalar_one()
        if anchored:
            raise RuntimeError("Remove asset-event blockchain records before downgrading revision 0008")
    dialect = op.get_context().dialect.name
    if dialect == "sqlite":
        for table in ("asset_events", "asset_ownerships"):
            op.execute(f"DROP TRIGGER IF EXISTS ck_{table}_no_update")
            op.execute(f"DROP TRIGGER IF EXISTS ck_{table}_no_delete")
    else:
        for table in ("asset_events", "asset_ownerships"):
            op.execute(f"DROP TRIGGER IF EXISTS ck_{table}_immutable ON {table}")
        op.execute("DROP FUNCTION IF EXISTS asset_history_guard()")
    with op.batch_alter_table("blockchain_records") as batch_op:
        batch_op.drop_constraint("ck_blockchain_records_record_reference", type_="check")
        batch_op.drop_constraint("uq_blockchain_records_asset_event_id", type_="unique")
        batch_op.drop_constraint("fk_blockchain_records_asset_event_id_asset_events", type_="foreignkey")
        batch_op.drop_column("asset_event_id")
        batch_op.alter_column("ledger_transaction_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_index("ix_asset_ownerships_organization", table_name="asset_ownerships")
    op.drop_index("ix_asset_ownerships_asset_created", table_name="asset_ownerships")
    op.drop_table("asset_ownerships")
    op.drop_index("ix_asset_events_actor_created", table_name="asset_events")
    op.drop_index("ix_asset_events_asset_sequence", table_name="asset_events")
    op.drop_table("asset_events")
    op.drop_index("ix_assets_product_id", table_name="assets")
    op.drop_index("ix_assets_custodian", table_name="assets")
    op.drop_index("ix_assets_owner_created", table_name="assets")
    op.drop_table("assets")
    op.drop_index("ix_products_organization_created", table_name="products")
    op.drop_table("products")


__all__ = ["downgrade", "upgrade"]


