"""internal account payments and exact balance tracking

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("account_number", sa.String(length=18), nullable=True))
    op.add_column(
        "organizations",
        sa.Column("balance", sa.Numeric(precision=18, scale=2), server_default=sa.text("0.00"), nullable=False),
    )

    if context.is_offline_mode():
        op.execute(
            sa.text(
                "WITH numbered AS (SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS row_number FROM organizations) "
                "UPDATE organizations AS organization "
                "SET account_number = '0' || LPAD(numbered.row_number::text, 17, '0') "
                "FROM numbered WHERE organization.id = numbered.id"
            )
        )
    else:
        bind = op.get_bind()
        organizations = sa.table("organizations", sa.column("id", sa.Uuid()))
        account_numbers = sa.table(
            "organizations", sa.column("id", sa.Uuid()), sa.column("account_number", sa.String(length=18))
        )
        for index, organization_id in enumerate(
            bind.execute(sa.select(organizations.c.id).order_by(organizations.c.id)).scalars(), start=1
        ):
            if index >= 10**17:
                raise RuntimeError("Too many organizations to backfill unique account numbers.")
            bind.execute(
                account_numbers.update()
                .where(account_numbers.c.id == organization_id)
                .values(account_number=f"0{index:017d}")
            )

    with op.batch_alter_table("organizations") as batch_op:
        batch_op.alter_column("account_number", existing_type=sa.String(length=18), nullable=False)
        batch_op.create_unique_constraint("uq_organizations_account_number", ["account_number"])
        batch_op.create_check_constraint("ck_organizations_account_number_length", "length(account_number) = 18")
        batch_op.create_check_constraint("ck_organizations_balance_non_negative", "balance >= 0")

    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=40), nullable=False),
        sa.Column("sender_organization_id", sa.Uuid(), nullable=False),
        sa.Column("sender_user_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_organization_id", sa.Uuid(), nullable=False),
        sa.Column("sender_account_number", sa.String(length=18), nullable=False),
        sa.Column("recipient_account_number", sa.String(length=18), nullable=False),
        sa.Column("recipient_name", sa.String(length=160), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("fee", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("total_debit", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column("purpose", sa.String(length=24), nullable=False),
        sa.Column("note", sa.String(length=140), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        sa.CheckConstraint("fee >= 0", name="ck_payments_fee_non_negative"),
        sa.CheckConstraint("total_debit = amount + fee", name="ck_payments_total_debit_matches"),
        sa.CheckConstraint("currency = 'INR'", name="ck_payments_currency"),
        sa.CheckConstraint(
            "purpose IN ('invoice', 'supplier', 'salary', 'personal', 'other')", name="ck_payments_purpose"
        ),
        sa.CheckConstraint("status IN ('pending', 'processing', 'completed')", name="ck_payments_status"),
        sa.ForeignKeyConstraint(
            ["sender_organization_id"], ["organizations.id"],
            name="fk_payments_sender_organization_id_organizations", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["sender_user_id"], ["users.id"], name="fk_payments_sender_user_id_users", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["recipient_organization_id"], ["organizations.id"],
            name="fk_payments_recipient_organization_id_organizations", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
        sa.UniqueConstraint("reference", name="uq_payments_reference"),
        sa.UniqueConstraint(
            "sender_organization_id", "idempotency_key", name="uq_payments_sender_idempotency"
        ),
    )
    op.create_index(
        "ix_payments_sender_created", "payments", ["sender_organization_id", "created_at"], unique=False
    )
    op.create_index(
        "ix_payments_recipient_created", "payments", ["recipient_organization_id", "created_at"], unique=False
    )
    op.create_index("ix_payments_status_created", "payments", ["status", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payments_status_created", table_name="payments")
    op.drop_index("ix_payments_recipient_created", table_name="payments")
    op.drop_index("ix_payments_sender_created", table_name="payments")
    op.drop_table("payments")
    with op.batch_alter_table("organizations") as batch_op:
        batch_op.drop_constraint("ck_organizations_balance_non_negative", type_="check")
        batch_op.drop_constraint("ck_organizations_account_number_length", type_="check")
        batch_op.drop_constraint("uq_organizations_account_number", type_="unique")
        batch_op.drop_column("balance")
        batch_op.drop_column("account_number")
