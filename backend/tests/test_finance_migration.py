from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, text


def test_payment_request_events_are_append_only_after_migration() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as connection:
            config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            connection.commit()
            user_id = uuid4().hex
            organization_id = uuid4().hex
            request_id = uuid4().hex
            event_id = uuid4().hex
            connection.execute(
                text("INSERT INTO users (id, email, password_hash, account_status, email_verified, created_at, updated_at) "
                     "VALUES (:id, 'finance-test@example.com', 'hash', 'active', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"),
                {"id": user_id},
            )
            connection.execute(
                text("INSERT INTO organizations (id, name, account_number, balance, account_type, status, created_at, updated_at) "
                     "VALUES (:id, 'Finance Test', '123456789012345678', 0, 'business', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"),
                {"id": organization_id},
            )
            connection.execute(
                text("INSERT INTO payment_requests (id, organization_id, requester_user_id, recipient_organization_id, "
                     "recipient_account_number, recipient_name, amount, purpose, idempotency_key, request_fingerprint) "
                     "VALUES (:id, :org, :user, :org, '123456789012345678', 'Finance Test', 1, 'invoice', 'key', 'fingerprint')"),
                {"id": request_id, "org": organization_id, "user": user_id},
            )
            connection.execute(
                text("INSERT INTO payment_request_events (id, payment_request_id, sequence_number, actor_user_id, from_status, to_status) "
                     "VALUES (:id, :request, 1, :user, NULL, 'DRAFT')"),
                {"id": event_id, "request": request_id, "user": user_id},
            )
            with pytest.raises(sa.exc.DatabaseError, match="append-only"):
                connection.execute(text("UPDATE payment_request_events SET detail = 'changed' WHERE id = :id"), {"id": event_id})
            connection.rollback()
    finally:
        engine.dispose()
