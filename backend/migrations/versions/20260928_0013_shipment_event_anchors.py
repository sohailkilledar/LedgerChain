"""allow existing blockchain records to anchor shipment events

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("blockchain_records") as batch_op:
        batch_op.drop_constraint(op.f("ck_blockchain_records_record_reference"), type_="check")
        batch_op.add_column(sa.Column("shipment_event_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_blockchain_records_shipment_event",
            "inventory_shipment_events",
            ["shipment_event_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_unique_constraint("uq_blockchain_records_shipment_event_id", ["shipment_event_id"])
        batch_op.create_check_constraint(
            "record_reference",
            "(ledger_transaction_id IS NOT NULL AND asset_event_id IS NULL AND shipment_event_id IS NULL) OR "
            "(ledger_transaction_id IS NULL AND asset_event_id IS NOT NULL AND shipment_event_id IS NULL) OR "
            "(ledger_transaction_id IS NULL AND asset_event_id IS NULL AND shipment_event_id IS NOT NULL)",
        )


def downgrade() -> None:
    if not op.get_context().as_sql:
        anchored = op.get_bind().execute(
            sa.text("SELECT count(*) FROM blockchain_records WHERE shipment_event_id IS NOT NULL")
        ).scalar_one()
        if anchored:
            raise RuntimeError("Remove shipment-event blockchain records before downgrading revision 0013")
    with op.batch_alter_table("blockchain_records") as batch_op:
        batch_op.drop_constraint(op.f("ck_blockchain_records_record_reference"), type_="check")
        batch_op.drop_constraint("uq_blockchain_records_shipment_event_id", type_="unique")
        batch_op.drop_constraint(
            "fk_blockchain_records_shipment_event", type_="foreignkey"
        )
        batch_op.drop_column("shipment_event_id")
        batch_op.create_check_constraint(
            "record_reference",
            "(ledger_transaction_id IS NOT NULL AND asset_event_id IS NULL) OR "
            "(ledger_transaction_id IS NULL AND asset_event_id IS NOT NULL)",
        )


__all__ = ["downgrade", "upgrade"]
