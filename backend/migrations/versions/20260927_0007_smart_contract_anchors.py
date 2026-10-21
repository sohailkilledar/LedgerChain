"""add smart-contract metadata and mined failure state

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("blockchain_records", sa.Column("contract_address", sa.String(length=42), nullable=True))
    op.add_column("blockchain_records", sa.Column("contract_version", sa.String(length=24), nullable=True))
    with op.batch_alter_table("blockchain_records") as batch_op:
        batch_op.drop_constraint("status", type_="check")
        batch_op.create_check_constraint(
            "status",
            "status IN ('submitting', 'submitted', 'confirmed', 'failed', 'submission_failed', 'simulated')",
        )
        batch_op.drop_constraint("failure_code_required", type_="check")
        batch_op.create_check_constraint(
            "failure_code_required",
            "status NOT IN ('submission_failed', 'failed') OR failure_code IS NOT NULL",
        )
        batch_op.create_check_constraint(
            "failed_transaction_fields",
            "status != 'failed' OR (transaction_hash IS NOT NULL AND confirmed_at IS NOT NULL)",
        )


def downgrade() -> None:
    if not op.get_context().as_sql:
        failed_records = op.get_bind().execute(
            sa.text("SELECT count(*) FROM blockchain_records WHERE status = 'failed'")
        ).scalar_one()
        if failed_records:
            raise RuntimeError("Resolve mined failed anchors before downgrading revision 0007")
    with op.batch_alter_table("blockchain_records") as batch_op:
        batch_op.drop_constraint("failed_transaction_fields", type_="check")
        batch_op.drop_constraint("failure_code_required", type_="check")
        batch_op.create_check_constraint(
            "failure_code_required",
            "status != 'submission_failed' OR failure_code IS NOT NULL",
        )
        batch_op.drop_constraint("status", type_="check")
        batch_op.create_check_constraint(
            "status",
            "status IN ('submitting', 'submitted', 'confirmed', 'submission_failed', 'simulated')",
        )
        batch_op.drop_column("contract_address")
        batch_op.drop_column("contract_version")


__all__ = ["downgrade", "upgrade"]
