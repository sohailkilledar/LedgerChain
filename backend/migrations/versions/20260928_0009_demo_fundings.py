"""record simulated bank funding approvals

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "demo_fundings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=40), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_demo_fundings_amount_positive"),
        sa.CheckConstraint("currency = 'INR'", name="ck_demo_fundings_currency"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference", name="uq_demo_fundings_reference"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_demo_fundings_idempotency"),
    )
    op.create_index("ix_demo_fundings_organization_created", "demo_fundings", ["organization_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_demo_fundings_organization_created", table_name="demo_fundings")
    op.drop_table("demo_fundings")

