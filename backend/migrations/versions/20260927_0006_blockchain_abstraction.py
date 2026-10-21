"""persist blockchain anchors for posted ledger transactions

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "blockchain_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ledger_transaction_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("network", sa.String(length=64), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=True),
        sa.Column("digest_version", sa.String(length=32), nullable=False),
        sa.Column("digest", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("transaction_hash", sa.String(length=256), nullable=True),
        sa.Column("block_number", sa.Integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('submitting', 'submitted', 'confirmed', 'submission_failed', 'simulated')",
            name="status",
        ),
        sa.CheckConstraint("length(digest) = 64", name="digest_length"),
        sa.CheckConstraint("chain_id IS NULL OR chain_id > 0", name="chain_id_positive"),
        sa.CheckConstraint(
            "status NOT IN ('submitted', 'confirmed') OR (transaction_hash IS NOT NULL AND submitted_at IS NOT NULL)",
            name="submitted_fields",
        ),
        sa.CheckConstraint(
            "status != 'confirmed' OR confirmed_at IS NOT NULL",
            name="confirmed_timestamp",
        ),
        sa.CheckConstraint(
            "status != 'submission_failed' OR failure_code IS NOT NULL",
            name="failure_code_required",
        ),
        sa.CheckConstraint(
            "status != 'simulated' OR (transaction_hash IS NULL AND block_number IS NULL AND submitted_at IS NULL AND confirmed_at IS NULL)",
            name="simulated_without_chain_data",
        ),
        sa.CheckConstraint("block_number IS NULL OR block_number >= 0", name="block_number_non_negative"),
        sa.ForeignKeyConstraint(
            ["ledger_transaction_id"],
            ["ledger_transactions.id"],
            name="fk_blockchain_records_ledger_transaction_id_ledger_transactions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_blockchain_records"),
        sa.UniqueConstraint("ledger_transaction_id", name="uq_blockchain_records_ledger_transaction_id"),
        sa.UniqueConstraint(
            "provider", "network", "transaction_hash", name="uq_blockchain_records_provider_network_transaction_hash"
        ),
    )
    op.create_index(
        "ix_blockchain_records_status_created",
        "blockchain_records",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_blockchain_records_status_created", table_name="blockchain_records")
    op.drop_table("blockchain_records")


__all__ = ["downgrade", "upgrade"]
