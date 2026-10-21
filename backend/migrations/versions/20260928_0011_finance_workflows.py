"""add organization-scoped budgets and payment request approvals

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATES = "'DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED', 'PAYMENT_CREATED', 'COMPLETED'"


def upgrade() -> None:
    op.create_table(
        "finance_budgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("category", sa.String(80)),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("allocated_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="INR", nullable=False),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("allocated_amount > 0", name="ck_finance_budgets_allocated_positive"),
        sa.CheckConstraint("period_start <= period_end", name="ck_finance_budgets_period_order"),
        sa.CheckConstraint("currency = 'INR'", name="ck_finance_budgets_currency"),
        sa.CheckConstraint("status IN ('active', 'closed')", name="ck_finance_budgets_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_finance_budgets_organization_period", "finance_budgets", ["organization_id", "period_start", "period_end"])

    op.create_table(
        "payment_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("requester_user_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_organization_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_account_number", sa.String(18), nullable=False),
        sa.Column("recipient_name", sa.String(160), nullable=False),
        sa.Column("budget_id", sa.Uuid()),
        sa.Column("category", sa.String(80)),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="INR", nullable=False),
        sa.Column("purpose", sa.String(24), nullable=False),
        sa.Column("note", sa.String(140)),
        sa.Column("status", sa.String(24), server_default="DRAFT", nullable=False),
        sa.Column("approver_user_id", sa.Uuid()),
        sa.Column("approval_note", sa.String(240)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("payment_id", sa.Uuid()),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("amount > 0", name="ck_payment_requests_amount_positive"),
        sa.CheckConstraint("currency = 'INR'", name="ck_payment_requests_currency"),
        sa.CheckConstraint("purpose IN ('invoice', 'supplier', 'salary', 'personal', 'other')", name="ck_payment_requests_purpose"),
        sa.CheckConstraint(f"status IN ({_STATES})", name="ck_payment_requests_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recipient_organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["budget_id"], ["finance_budgets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approver_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "requester_user_id", "idempotency_key", name="uq_payment_request_idempotency"),
        sa.UniqueConstraint("payment_id", name="uq_payment_request_payment"),
    )
    op.create_index("ix_payment_requests_organization_status_created", "payment_requests", ["organization_id", "status", "created_at"])
    op.create_index("ix_payment_requests_budget_status", "payment_requests", ["budget_id", "status"])

    op.create_table(
        "payment_request_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payment_request_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(24)),
        sa.Column("to_status", sa.String(24), nullable=False),
        sa.Column("detail", sa.String(240)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(f"to_status IN ({_STATES})", name="ck_payment_request_events_to_status"),
        sa.CheckConstraint(f"from_status IS NULL OR from_status IN ({_STATES})", name="ck_payment_request_events_from_status"),
        sa.CheckConstraint("sequence_number > 0", name="ck_payment_request_events_sequence_positive"),
        sa.ForeignKeyConstraint(["payment_request_id"], ["payment_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_request_id", "sequence_number", name="uq_payment_request_event_sequence"),
    )
    op.create_index("ix_payment_request_events_request_created", "payment_request_events", ["payment_request_id", "sequence_number"])

    if op.get_context().dialect.name == "sqlite":
        op.execute("CREATE TRIGGER ck_payment_request_events_no_update BEFORE UPDATE ON payment_request_events BEGIN SELECT RAISE(ABORT, 'payment request history is append-only'); END")
        op.execute("CREATE TRIGGER ck_payment_request_events_no_delete BEFORE DELETE ON payment_request_events BEGIN SELECT RAISE(ABORT, 'payment request history is append-only'); END")
    else:
        op.execute("CREATE FUNCTION payment_request_event_guard() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'payment request history is append-only' USING ERRCODE = '23514'; END; $$")
        op.execute("CREATE TRIGGER ck_payment_request_events_immutable BEFORE UPDATE OR DELETE ON payment_request_events FOR EACH ROW EXECUTE FUNCTION payment_request_event_guard()")


def downgrade() -> None:
    if op.get_context().dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS ck_payment_request_events_no_update")
        op.execute("DROP TRIGGER IF EXISTS ck_payment_request_events_no_delete")
    else:
        op.execute("DROP TRIGGER IF EXISTS ck_payment_request_events_immutable ON payment_request_events")
        op.execute("DROP FUNCTION IF EXISTS payment_request_event_guard()")
    op.drop_index("ix_payment_request_events_request_created", table_name="payment_request_events")
    op.drop_table("payment_request_events")
    op.drop_index("ix_payment_requests_budget_status", table_name="payment_requests")
    op.drop_index("ix_payment_requests_organization_status_created", table_name="payment_requests")
    op.drop_table("payment_requests")
    op.drop_index("ix_finance_budgets_organization_period", table_name="finance_budgets")
    op.drop_table("finance_budgets")
