from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, text


def test_asset_events_and_ownership_rows_are_database_append_only() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as connection:
            config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            connection.commit()
            event_id = uuid4().hex
            asset_id = uuid4().hex
            connection.execute(
                text(
                    "INSERT INTO asset_events "
                    "(id, asset_id, sequence_number, event_type, actor_user_id, actor_organization_id, "
                    "resulting_state, metadata, idempotency_key, request_fingerprint) "
                    "VALUES (:id, :asset_id, 1, 'REGISTERED', :user_id, :organization_id, '{}', '{}', 'key-1', 'fingerprint')"
                ),
                {"id": event_id, "asset_id": asset_id, "user_id": uuid4().hex, "organization_id": uuid4().hex},
            )
            with pytest.raises(sa.exc.DatabaseError, match="append-only"):
                connection.execute(text("UPDATE asset_events SET event_type = 'RETIRED' WHERE id = :id"), {"id": event_id})
            connection.rollback()

            ownership_id = uuid4().hex
            connection.execute(
                text(
                    "INSERT INTO asset_ownerships (id, asset_id, organization_id, event_id) "
                    "VALUES (:id, :asset_id, :organization_id, :event_id)"
                ),
                {"id": ownership_id, "asset_id": asset_id, "organization_id": uuid4().hex, "event_id": event_id},
            )
            with pytest.raises(sa.exc.DatabaseError, match="append-only"):
                connection.execute(text("DELETE FROM asset_ownerships WHERE id = :id"), {"id": ownership_id})
            connection.rollback()

            with pytest.raises(sa.exc.IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO blockchain_records "
                        "(id, provider, network, digest_version, digest, status) "
                        "VALUES (:id, 'development', 'local-simulation', 'ledgerchain-asset-event-v1', :digest, 'simulated')"
                    ),
                    {"id": uuid4().hex, "digest": "a" * 64},
                )
    finally:
        engine.dispose()


