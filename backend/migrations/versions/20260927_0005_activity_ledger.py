"""off-chain double-entry ledger and append-only history

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-27
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import context, op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ledger_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=40), nullable=False),
        sa.Column("transaction_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("transaction_type IN ('payment_transfer')", name="ck_ledger_transactions_transaction_type"),
        sa.CheckConstraint("status IN ('draft', 'posted')", name="ck_ledger_transactions_status"),
        sa.CheckConstraint(
            "status != 'posted' OR posted_at IS NOT NULL", name="ck_ledger_transactions_posted_timestamp"
        ),
        sa.CheckConstraint("amount > 0", name="ck_ledger_transactions_amount_positive"),
        sa.CheckConstraint("currency = 'INR'", name="ck_ledger_transactions_currency"),
        sa.ForeignKeyConstraint(
            ["payment_id"], ["payments.id"],
            name="fk_ledger_transactions_payment_id_payments", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ledger_transactions"),
        sa.UniqueConstraint("payment_id", name="uq_ledger_transactions_payment_id"),
        sa.UniqueConstraint("reference", name="uq_ledger_transactions_reference"),
    )
    op.create_index(
        "ix_ledger_transactions_created_at", "ledger_transactions", ["created_at"], unique=False
    )
    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ledger_transaction_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("description", sa.String(length=160), nullable=True),
        sa.CheckConstraint("direction IN ('debit', 'credit')", name="ck_ledger_entries_direction"),
        sa.CheckConstraint("amount > 0", name="ck_ledger_entries_amount_positive"),
        sa.CheckConstraint("currency = 'INR'", name="ck_ledger_entries_currency"),
        sa.ForeignKeyConstraint(
            ["ledger_transaction_id"], ["ledger_transactions.id"],
            name="fk_ledger_entries_ledger_transaction_id_ledger_transactions", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["organizations.id"],
            name="fk_ledger_entries_account_id_organizations", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ledger_entries"),
    )
    op.create_index(
        "ix_ledger_entries_account_created", "ledger_entries", ["account_id", "created_at"], unique=False
    )
    op.create_index(
        "ix_ledger_entries_transaction_id", "ledger_entries", ["ledger_transaction_id"], unique=False
    )
    _create_append_only_triggers()
    _backfill_completed_payments()


def _backfill_completed_payments() -> None:
    if context.is_offline_mode():
        op.execute(
            "INSERT INTO ledger_transactions "
            "(id, payment_id, reference, transaction_type, status, currency, amount, created_at) "
            "SELECT gen_random_uuid(), id, reference, 'payment_transfer', 'draft', currency, amount, completed_at "
            "FROM payments WHERE status = 'completed'"
        )
        op.execute(
            "INSERT INTO ledger_entries "
            "(id, ledger_transaction_id, account_id, direction, amount, currency, created_at, description) "
            "SELECT gen_random_uuid(), ledger.id, payment.sender_organization_id, 'debit', "
            "payment.total_debit, payment.currency, payment.completed_at, 'Internal payment sent' "
            "FROM payments AS payment JOIN ledger_transactions AS ledger ON ledger.payment_id = payment.id "
            "WHERE payment.status = 'completed'"
        )
        op.execute(
            "INSERT INTO ledger_entries "
            "(id, ledger_transaction_id, account_id, direction, amount, currency, created_at, description) "
            "SELECT gen_random_uuid(), ledger.id, payment.recipient_organization_id, 'credit', "
            "payment.amount, payment.currency, payment.completed_at, 'Internal payment received' "
            "FROM payments AS payment JOIN ledger_transactions AS ledger ON ledger.payment_id = payment.id "
            "WHERE payment.status = 'completed'"
        )
        op.execute(
            "UPDATE ledger_transactions SET status = 'posted', posted_at = created_at WHERE status = 'draft'"
        )
        return

    bind = op.get_bind()
    payments = sa.table(
        "payments",
        sa.column("id", sa.Uuid()),
        sa.column("reference", sa.String(40)),
        sa.column("sender_organization_id", sa.Uuid()),
        sa.column("recipient_organization_id", sa.Uuid()),
        sa.column("amount", sa.Numeric(18, 2)),
        sa.column("total_debit", sa.Numeric(18, 2)),
        sa.column("currency", sa.String(3)),
        sa.column("status", sa.String(16)),
        sa.column("completed_at", sa.DateTime(timezone=True)),
    )
    transactions = sa.table(
        "ledger_transactions",
        sa.column("id", sa.Uuid()),
        sa.column("payment_id", sa.Uuid()),
        sa.column("reference", sa.String(40)),
        sa.column("transaction_type", sa.String(32)),
        sa.column("status", sa.String(16)),
        sa.column("currency", sa.String(3)),
        sa.column("amount", sa.Numeric(18, 2)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("posted_at", sa.DateTime(timezone=True)),
    )
    entries = sa.table(
        "ledger_entries",
        sa.column("id", sa.Uuid()),
        sa.column("ledger_transaction_id", sa.Uuid()),
        sa.column("account_id", sa.Uuid()),
        sa.column("direction", sa.String(8)),
        sa.column("amount", sa.Numeric(18, 2)),
        sa.column("currency", sa.String(3)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("description", sa.String(160)),
    )
    statement = sa.select(
        payments.c.id,
        payments.c.reference,
        payments.c.sender_organization_id,
        payments.c.recipient_organization_id,
        payments.c.amount,
        payments.c.total_debit,
        payments.c.currency,
        payments.c.completed_at,
    ).where(payments.c.status == "completed")
    for payment in bind.execute(statement).mappings():
        if payment["amount"] != payment["total_debit"]:
            raise RuntimeError("Cannot backfill a completed payment whose debit and credit are unbalanced.")
        transaction_id = uuid4()
        completed_at = payment["completed_at"]
        bind.execute(
            transactions.insert().values(
                id=transaction_id,
                payment_id=payment["id"],
                reference=payment["reference"],
                transaction_type="payment_transfer",
                status="draft",
                currency=payment["currency"],
                amount=payment["amount"],
                created_at=completed_at,
            )
        )
        bind.execute(
            entries.insert().values(
                id=uuid4(),
                ledger_transaction_id=transaction_id,
                account_id=payment["sender_organization_id"],
                direction="debit",
                amount=payment["total_debit"],
                currency=payment["currency"],
                created_at=completed_at,
                description="Internal payment sent",
            )
        )
        bind.execute(
            entries.insert().values(
                id=uuid4(),
                ledger_transaction_id=transaction_id,
                account_id=payment["recipient_organization_id"],
                direction="credit",
                amount=payment["amount"],
                currency=payment["currency"],
                created_at=completed_at,
                description="Internal payment received",
            )
        )
        bind.execute(
            transactions.update()
            .where(transactions.c.id == transaction_id)
            .values(status="posted", posted_at=completed_at)
        )


def _create_append_only_triggers() -> None:
    dialect = op.get_context().dialect.name
    if dialect == "sqlite":
        op.execute(
            "CREATE TRIGGER ck_ledger_transactions_balanced "
            "BEFORE UPDATE OF status ON ledger_transactions WHEN NEW.status = 'posted' BEGIN "
            "SELECT CASE WHEN "
            "(SELECT COUNT(*) FROM ledger_entries WHERE ledger_transaction_id = NEW.id AND direction = 'debit') < 1 "
            "OR (SELECT COUNT(*) FROM ledger_entries WHERE ledger_transaction_id = NEW.id AND direction = 'credit') < 1 "
            "OR (SELECT COALESCE(SUM(amount), 0) FROM ledger_entries WHERE ledger_transaction_id = NEW.id AND direction = 'debit') "
            "!= (SELECT COALESCE(SUM(amount), 0) FROM ledger_entries WHERE ledger_transaction_id = NEW.id AND direction = 'credit') "
            "OR (SELECT COALESCE(SUM(amount), 0) FROM ledger_entries WHERE ledger_transaction_id = NEW.id AND direction = 'debit') "
            "!= NEW.amount THEN RAISE(ABORT, 'ledger transaction is unbalanced') END; END"
        )
        op.execute(
            "CREATE TRIGGER ck_ledger_transactions_insert_draft "
            "BEFORE INSERT ON ledger_transactions WHEN NEW.status != 'draft' BEGIN "
            "SELECT RAISE(ABORT, 'ledger transaction must be created as draft'); END"
        )
        op.execute(
            "CREATE TRIGGER ck_ledger_entries_insert_draft "
            "BEFORE INSERT ON ledger_entries WHEN "
            "(SELECT status FROM ledger_transactions WHERE id = NEW.ledger_transaction_id) != 'draft' BEGIN "
            "SELECT RAISE(ABORT, 'cannot append entries to a posted ledger transaction'); END"
        )
        op.execute(
            "CREATE TRIGGER ck_ledger_entries_no_update BEFORE UPDATE ON ledger_entries BEGIN "
            "SELECT RAISE(ABORT, 'ledger entries are append-only'); END"
        )
        op.execute(
            "CREATE TRIGGER ck_ledger_entries_no_delete BEFORE DELETE ON ledger_entries BEGIN "
            "SELECT RAISE(ABORT, 'ledger entries are append-only'); END"
        )
        op.execute(
            "CREATE TRIGGER ck_ledger_transactions_no_update BEFORE UPDATE ON ledger_transactions "
            "WHEN OLD.status = 'posted' BEGIN "
            "SELECT RAISE(ABORT, 'posted ledger transactions are immutable'); END"
        )
        op.execute(
            "CREATE TRIGGER ck_ledger_transactions_no_delete BEFORE DELETE ON ledger_transactions "
            "WHEN OLD.status = 'posted' BEGIN "
            "SELECT RAISE(ABORT, 'posted ledger transactions are immutable'); END"
        )
        op.execute(
            "CREATE TRIGGER ck_payments_completed_no_update BEFORE UPDATE ON payments "
            "WHEN OLD.status = 'completed' BEGIN "
            "SELECT RAISE(ABORT, 'completed payments are immutable'); END"
        )
        op.execute(
            "CREATE TRIGGER ck_payments_completed_no_delete BEFORE DELETE ON payments "
            "WHEN OLD.status = 'completed' BEGIN "
            "SELECT RAISE(ABORT, 'completed payments are immutable'); END"
        )
        return

    op.execute(
        "CREATE FUNCTION ledger_assert_balanced() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "DECLARE current_status text; transaction_amount numeric; debit_count bigint; credit_count bigint; "
        "debit_total numeric; credit_total numeric; BEGIN "
        "SELECT status, amount INTO current_status, transaction_amount FROM ledger_transactions WHERE id = NEW.id; "
        "IF current_status = 'posted' THEN "
        "SELECT COUNT(*) FILTER (WHERE direction = 'debit'), "
        "COUNT(*) FILTER (WHERE direction = 'credit'), "
        "COALESCE(SUM(amount) FILTER (WHERE direction = 'debit'), 0), "
        "COALESCE(SUM(amount) FILTER (WHERE direction = 'credit'), 0) "
        "INTO debit_count, credit_count, debit_total, credit_total "
        "FROM ledger_entries WHERE ledger_transaction_id = NEW.id; "
        "IF debit_count < 1 OR credit_count < 1 OR debit_total <> credit_total "
        "OR debit_total <> transaction_amount THEN "
        "RAISE EXCEPTION 'ledger transaction is unbalanced' USING ERRCODE = '23514'; END IF; "
        "END IF; RETURN NULL; END; $$"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER ck_ledger_transactions_balanced "
        "AFTER INSERT OR UPDATE ON ledger_transactions DEFERRABLE INITIALLY DEFERRED "
        "FOR EACH ROW EXECUTE FUNCTION ledger_assert_balanced()"
    )
    op.execute(
        "CREATE FUNCTION ledger_assert_payment_posted() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "DECLARE current_status text; BEGIN "
        "SELECT status INTO current_status FROM payments WHERE id = NEW.id; "
        "IF current_status = 'completed' AND NOT EXISTS ("
        "SELECT 1 FROM ledger_transactions WHERE payment_id = NEW.id AND status = 'posted'"
        ") THEN RAISE EXCEPTION 'completed payment has no posted ledger transaction' "
        "USING ERRCODE = '23514'; END IF; RETURN NULL; END; $$"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER ck_payments_have_posted_ledger "
        "AFTER INSERT OR UPDATE ON payments DEFERRABLE INITIALLY DEFERRED "
        "FOR EACH ROW EXECUTE FUNCTION ledger_assert_payment_posted()"
    )
    op.execute(
        "CREATE FUNCTION ledger_guard_payment() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN IF OLD.status = 'completed' THEN RAISE EXCEPTION 'completed payments are immutable' "
        "USING ERRCODE = '23514'; END IF; "
        "IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$"
    )
    op.execute(
        "CREATE TRIGGER ck_payments_completed_immutable BEFORE UPDATE OR DELETE ON payments "
        "FOR EACH ROW EXECUTE FUNCTION ledger_guard_payment()"
    )
    op.execute(
        "CREATE FUNCTION ledger_guard_transaction() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN IF OLD.status = 'posted' THEN RAISE EXCEPTION 'posted ledger transactions are immutable' "
        "USING ERRCODE = '23514'; END IF; "
        "IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$"
    )
    op.execute(
        "CREATE TRIGGER ck_ledger_transactions_immutable BEFORE UPDATE OR DELETE ON ledger_transactions "
        "FOR EACH ROW EXECUTE FUNCTION ledger_guard_transaction()"
    )
    op.execute(
        "CREATE FUNCTION ledger_guard_entry() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "DECLARE transaction_status text; BEGIN "
        "IF TG_OP = 'INSERT' THEN "
        "SELECT status INTO transaction_status FROM ledger_transactions WHERE id = NEW.ledger_transaction_id; "
        "IF transaction_status <> 'draft' THEN RAISE EXCEPTION 'cannot append entries to a posted ledger transaction' "
        "USING ERRCODE = '23514'; END IF; RETURN NEW; END IF; "
        "RAISE EXCEPTION 'ledger entries are append-only' USING ERRCODE = '23514'; END; $$"
    )
    op.execute(
        "CREATE TRIGGER ck_ledger_entries_immutable BEFORE INSERT OR UPDATE OR DELETE ON ledger_entries "
        "FOR EACH ROW EXECUTE FUNCTION ledger_guard_entry()"
    )


def downgrade() -> None:
    dialect = op.get_context().dialect.name
    if dialect == "sqlite":
        for trigger in (
            "ck_ledger_transactions_balanced",
            "ck_ledger_transactions_insert_draft",
            "ck_ledger_entries_insert_draft",
            "ck_ledger_entries_no_update",
            "ck_ledger_entries_no_delete",
            "ck_ledger_transactions_no_update",
            "ck_ledger_transactions_no_delete",
            "ck_payments_completed_no_update",
            "ck_payments_completed_no_delete",
        ):
            op.execute(f"DROP TRIGGER IF EXISTS {trigger}")
    else:
        op.execute("DROP TRIGGER IF EXISTS ck_ledger_entries_immutable ON ledger_entries")
        op.execute("DROP TRIGGER IF EXISTS ck_ledger_transactions_immutable ON ledger_transactions")
        op.execute("DROP TRIGGER IF EXISTS ck_ledger_transactions_balanced ON ledger_transactions")
        op.execute("DROP TRIGGER IF EXISTS ck_payments_have_posted_ledger ON payments")
        op.execute("DROP TRIGGER IF EXISTS ck_payments_completed_immutable ON payments")
        op.execute("DROP FUNCTION IF EXISTS ledger_guard_entry()")
        op.execute("DROP FUNCTION IF EXISTS ledger_guard_transaction()")
        op.execute("DROP FUNCTION IF EXISTS ledger_guard_payment()")
        op.execute("DROP FUNCTION IF EXISTS ledger_assert_payment_posted()")
        op.execute("DROP FUNCTION IF EXISTS ledger_assert_balanced()")
    op.drop_index("ix_ledger_entries_transaction_id", table_name="ledger_entries")
    op.drop_index("ix_ledger_entries_account_created", table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_index("ix_ledger_transactions_created_at", table_name="ledger_transactions")
    op.drop_table("ledger_transactions")


__all__ = ["downgrade", "upgrade"]
