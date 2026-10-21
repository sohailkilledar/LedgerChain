from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, text


def test_ledger_migration_backfills_completed_payment_history() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as connection:
            config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "0004")
            sender_org_id = uuid4().hex
            recipient_org_id = uuid4().hex
            payment_id = uuid4().hex
            payment_time = "2026-09-26 12:30:00"
            connection.execute(
                text(
                    "INSERT INTO organizations "
                    "(id, name, account_number, balance, account_type, status) "
                    "VALUES (:id, 'Sender', '100000000000000001', 400.00, 'business', 'active')"
                ),
                {"id": sender_org_id},
            )
            connection.execute(
                text(
                    "INSERT INTO organizations "
                    "(id, name, account_number, balance, account_type, status) "
                    "VALUES (:id, 'Recipient', '100000000000000002', 100.00, 'business', 'active')"
                ),
                {"id": recipient_org_id},
            )
            connection.execute(
                text(
                    "INSERT INTO payments "
                    "(id, reference, sender_organization_id, sender_user_id, recipient_organization_id, "
                    "sender_account_number, recipient_account_number, recipient_name, amount, fee, total_debit, "
                    "currency, purpose, status, idempotency_key, request_fingerprint, created_at, updated_at, completed_at) "
                    "VALUES (:id, 'LC-PAY-BACKFILL-001', :sender, :sender_user, :recipient, "
                    "'100000000000000001', '100000000000000002', 'Recipient', 25.50, 0.00, 25.50, "
                    "'INR', 'invoice', 'completed', 'migration-key-001', 'fingerprint', :completed_at, :completed_at, :completed_at)"
                ),
                {
                    "id": payment_id,
                    "sender": sender_org_id,
                    "sender_user": uuid4().hex,
                    "recipient": recipient_org_id,
                    "completed_at": payment_time,
                },
            )
            connection.commit()
            command.upgrade(config, "head")
            transaction = connection.execute(
                text(
                    "SELECT id, status, reference, amount, created_at, posted_at "
                    "FROM ledger_transactions WHERE payment_id = :payment_id"
                ),
                {"payment_id": payment_id},
            ).first()
            assert transaction is not None
            assert transaction.status == "posted"
            assert transaction.reference == "LC-PAY-BACKFILL-001"
            assert transaction.amount == 25.50
            assert transaction.created_at == transaction.posted_at
            entries = connection.execute(
                text(
                    "SELECT direction, amount, account_id FROM ledger_entries "
                    "WHERE ledger_transaction_id = :transaction_id ORDER BY direction"
                ),
                {"transaction_id": transaction.id},
            ).all()
            assert [(entry.direction, entry.amount) for entry in entries] == [
                ("credit", 25.5),
                ("debit", 25.5),
            ]
            assert len({entry.account_id for entry in entries}) == 2
    finally:
        engine.dispose()


def test_ledger_migration_enforces_double_entry_and_append_only_history() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as connection:
            config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            connection.commit()

            transaction_id = uuid4().hex
            payment_id = uuid4().hex
            connection.execute(
                text(
                    "INSERT INTO ledger_transactions "
                    "(id, payment_id, reference, transaction_type, status, currency, amount) "
                    "VALUES (:id, :payment_id, :reference, 'payment_transfer', 'draft', 'INR', 15.25)"
                ),
                {"id": transaction_id, "payment_id": payment_id, "reference": "LC-LEDGER-TEST-01"},
            )
            for entry_id, account_id, direction in (
                (uuid4().hex, uuid4().hex, "debit"),
                (uuid4().hex, uuid4().hex, "credit"),
            ):
                connection.execute(
                    text(
                        "INSERT INTO ledger_entries "
                        "(id, ledger_transaction_id, account_id, direction, amount, currency) "
                        "VALUES (:id, :transaction_id, :account_id, :direction, 15.25, 'INR')"
                    ),
                    {
                        "id": entry_id,
                        "transaction_id": transaction_id,
                        "account_id": account_id,
                        "direction": direction,
                    },
                )
            connection.execute(
                text("UPDATE ledger_transactions SET status = 'posted', posted_at = CURRENT_TIMESTAMP WHERE id = :id"),
                {"id": transaction_id},
            )
            connection.commit()

            with pytest.raises(sa.exc.IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO ledger_transactions "
                        "(id, payment_id, reference, transaction_type, status, currency, amount) "
                        "VALUES (:id, :payment_id, :reference, 'payment_transfer', 'draft', 'INR', 15.25)"
                    ),
                    {
                        "id": uuid4().hex,
                        "payment_id": payment_id,
                        "reference": "LC-LEDGER-DUPLICATE-01",
                    },
                )
            connection.rollback()
            with pytest.raises(sa.exc.DatabaseError, match="append-only"):
                connection.execute(
                    text("UPDATE ledger_entries SET amount = 99 WHERE ledger_transaction_id = :id"),
                    {"id": transaction_id},
                )
            connection.rollback()
            with pytest.raises(sa.exc.DatabaseError, match="append-only"):
                connection.execute(
                    text("DELETE FROM ledger_entries WHERE ledger_transaction_id = :id"),
                    {"id": transaction_id},
                )
            connection.rollback()
            with pytest.raises(sa.exc.DatabaseError, match="immutable"):
                connection.execute(
                    text("UPDATE ledger_transactions SET amount = 99 WHERE id = :id"),
                    {"id": transaction_id},
                )
            connection.rollback()
            with pytest.raises(sa.exc.DatabaseError, match="cannot append entries"):
                connection.execute(
                    text(
                        "INSERT INTO ledger_entries "
                        "(id, ledger_transaction_id, account_id, direction, amount, currency) "
                        "VALUES (:id, :transaction_id, :account_id, 'debit', 15.25, 'INR')"
                    ),
                    {
                        "id": uuid4().hex,
                        "transaction_id": transaction_id,
                        "account_id": uuid4().hex,
                    },
                )
            connection.rollback()

            unbalanced_id = uuid4().hex
            connection.execute(
                text(
                    "INSERT INTO ledger_transactions "
                    "(id, payment_id, reference, transaction_type, status, currency, amount) "
                    "VALUES (:id, :payment_id, :reference, 'payment_transfer', 'draft', 'INR', 15.25)"
                ),
                {"id": unbalanced_id, "payment_id": uuid4().hex, "reference": "LC-LEDGER-TEST-02"},
            )
            connection.execute(
                text(
                    "INSERT INTO ledger_entries "
                    "(id, ledger_transaction_id, account_id, direction, amount, currency) "
                    "VALUES (:id, :transaction_id, :account_id, 'debit', 15.25, 'INR')"
                ),
                {"id": uuid4().hex, "transaction_id": unbalanced_id, "account_id": uuid4().hex},
            )
            with pytest.raises(sa.exc.DatabaseError, match="unbalanced"):
                connection.execute(
                    text("UPDATE ledger_transactions SET status = 'posted', posted_at = CURRENT_TIMESTAMP WHERE id = :id"),
                    {"id": unbalanced_id},
                )
            connection.rollback()
    finally:
        engine.dispose()


def test_ledger_database_constraints_reject_invalid_entry_values() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as connection:
            config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            transaction_id = uuid4().hex
            connection.execute(
                text(
                    "INSERT INTO ledger_transactions "
                    "(id, payment_id, reference, transaction_type, status, currency, amount) "
                    "VALUES (:id, :payment_id, :reference, 'payment_transfer', 'draft', 'INR', 1.00)"
                ),
                {"id": transaction_id, "payment_id": uuid4().hex, "reference": "LC-LEDGER-CHECKS-01"},
            )
            for direction, amount in (("other", "1.00"), ("debit", "0.00"), ("credit", "-1.00")):
                with pytest.raises(sa.exc.IntegrityError):
                    connection.execute(
                        text(
                            "INSERT INTO ledger_entries "
                            "(id, ledger_transaction_id, account_id, direction, amount, currency) "
                            "VALUES (:id, :transaction_id, :account_id, :direction, :amount, 'INR')"
                        ),
                        {
                            "id": uuid4().hex,
                            "transaction_id": transaction_id,
                            "account_id": uuid4().hex,
                            "direction": direction,
                            "amount": amount,
                        },
                    )
                connection.rollback()
                connection.execute(
                    text(
                        "INSERT INTO ledger_transactions "
                        "(id, payment_id, reference, transaction_type, status, currency, amount) "
                        "VALUES (:id, :payment_id, :reference, 'payment_transfer', 'draft', 'INR', 1.00)"
                    ),
                    {"id": transaction_id, "payment_id": uuid4().hex, "reference": f"LC-LEDGER-CHECKS-{direction}"},
                )
            connection.rollback()
    finally:
        engine.dispose()


def test_ledger_migration_contains_account_payment_and_posting_constraints() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as connection:
            config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            metadata = sa.MetaData()
            transactions = sa.Table("ledger_transactions", metadata, autoload_with=connection)
            entries = sa.Table("ledger_entries", metadata, autoload_with=connection)
            transaction_fks = {tuple(fk.column_keys) for fk in transactions.foreign_key_constraints}
            entry_fks = {tuple(fk.column_keys) for fk in entries.foreign_key_constraints}
            assert ("payment_id",) in transaction_fks
            assert ("ledger_transaction_id",) in entry_fks
            assert ("account_id",) in entry_fks
            assert any(constraint.name == "uq_ledger_transactions_payment_id" for constraint in transactions.constraints)
    finally:
        engine.dispose()


def test_ledger_migration_generates_postgresql_sql() -> None:
    from io import StringIO

    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.attributes["configure_logger"] = False
    output = StringIO()
    config.output_buffer = output
    command.upgrade(config, "head", sql=True)
    generated = output.getvalue()
    assert "CREATE CONSTRAINT TRIGGER ck_ledger_transactions_balanced" in generated
    assert "DEFERRABLE INITIALLY DEFERRED" in generated
    assert "CREATE TRIGGER ck_ledger_entries_immutable" in generated
    assert "CREATE TABLE ledger_entries" in generated
    assert "CREATE TABLE blockchain_records" in generated
    assert "uq_blockchain_records_ledger_transaction_id" in generated
    assert "NUMERIC(18, 2)" in generated


def test_blockchain_migration_enforces_record_state_and_one_anchor_per_ledger_transaction() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as connection:
            config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            metadata = sa.MetaData()
            records = sa.Table("blockchain_records", metadata, autoload_with=connection)
            assert {tuple(fk.column_keys) for fk in records.foreign_key_constraints} == {
                ("ledger_transaction_id",),
                ("asset_event_id",),
                ("shipment_event_id",),
            }
            assert any(
                isinstance(constraint, sa.UniqueConstraint)
                and tuple(column.name for column in constraint.columns) == ("ledger_transaction_id",)
                for constraint in records.constraints
            )

            ledger_id = uuid4().hex
            connection.execute(
                text(
                    "INSERT INTO blockchain_records "
                    "(id, ledger_transaction_id, provider, network, digest_version, digest, status) "
                    "VALUES (:id, :ledger_id, 'development', 'local-simulation', 'ledgerchain-ledger-v1', :digest, 'simulated')"
                ),
                {"id": uuid4().hex, "ledger_id": ledger_id, "digest": "a" * 64},
            )
            with pytest.raises(sa.exc.IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO blockchain_records "
                        "(id, ledger_transaction_id, provider, network, digest_version, digest, status) "
                        "VALUES (:id, :ledger_id, 'development', 'local-simulation', 'ledgerchain-ledger-v1', :digest, 'simulated')"
                    ),
                    {"id": uuid4().hex, "ledger_id": ledger_id, "digest": "b" * 64},
                )
            connection.rollback()
            with pytest.raises(sa.exc.IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO blockchain_records "
                        "(id, ledger_transaction_id, provider, network, digest_version, digest, status) "
                        "VALUES (:id, :ledger_id, 'development', 'local-simulation', 'ledgerchain-ledger-v1', :digest, 'confirmed')"
                    ),
                    {"id": uuid4().hex, "ledger_id": uuid4().hex, "digest": "c" * 64},
                )
            connection.rollback()
    finally:
        engine.dispose()


__all__ = []
