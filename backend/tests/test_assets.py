
import pytest

pytestmark = pytest.mark.skip(
    reason='Asset creation, transfer, custody, retirement and verification logic is intentionally excluded from this public source distribution.',
)

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from app.blockchain.provider import AnchorPayload, ProviderAnchor, ProviderHealth, ProviderTransaction
from app.core.config import Settings
from app.db.base import Base
from app.db.session import Database, create_session_factory
from app.main import create_app
from app.models.account import Organization, OrganizationMembership
from app.models.asset import AssetEvent, AssetOwnership
from app.models.auth import User
from app.models.blockchain import BlockchainRecord
from app.services.blockchain import BlockchainService
from tests.test_payments import _headers, _register_and_login


@pytest.fixture
def payment_world() -> Iterator[dict[str, Any]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    database = Database(engine=engine, session_factory=create_session_factory(engine))
    app = create_app(Settings(_env_file=None, environment="test", cors_origins="http://localhost:3000"), database)
    with TestClient(app, raise_server_exceptions=False) as sender, TestClient(
        app, raise_server_exceptions=False
    ) as recipient, TestClient(app, raise_server_exceptions=False) as outsider:
        sender_user_id, _ = _register_and_login(sender, "asset-sender@example.com")
        recipient_user_id, _ = _register_and_login(recipient, "asset-recipient@example.com")
        outsider_user_id, _ = _register_and_login(outsider, "asset-outsider@example.com")
        with database.session_factory() as session:
            sender_membership = session.scalar(
                select(OrganizationMembership).where(OrganizationMembership.user_id == sender_user_id)
            )
            recipient_membership = session.scalar(
                select(OrganizationMembership).where(OrganizationMembership.user_id == recipient_user_id)
            )
            assert sender_membership is not None and recipient_membership is not None
            sender_organization = session.get(Organization, sender_membership.organization_id)
            recipient_organization = session.get(Organization, recipient_membership.organization_id)
            assert sender_organization is not None and recipient_organization is not None
            yield {
                "database": database,
                "sender": sender,
                "recipient": recipient,
                "outsider": outsider,
                "sender_user_id": sender_user_id,
                "recipient_user_id": recipient_user_id,
                "outsider_user_id": outsider_user_id,
                "sender_organization_id": sender_membership.organization_id,
                "recipient_organization_id": recipient_membership.organization_id,
                "sender_account_number": sender_organization.account_number,
                "recipient_account_number": recipient_organization.account_number,
            }
    database.dispose()


def _client(world: dict[str, Any]) -> TestClient:
    client = world["sender"]
    assert isinstance(client, TestClient)
    return client


def _create_asset(client: TestClient, world: dict[str, Any], identifier: str = "MACHINE-0001"):
    return client.post(
        "/api/v1/assets",
        headers=_headers(client),
        json={
            "organization_id": str(world["sender_organization_id"]),
            "asset_identifier": identifier,
            "category": "equipment",
            "name": "Packaging machine",
            "description": "Line 4 packaging machine",
            "metadata": {"serial": "SN-2044", "model": "Pack-100"},
        },
    )


class ConfirmingAssetProvider:
    provider_id = "test-provider"
    network = "local-simulation"

    def __init__(self) -> None:
        self.payload: AnchorPayload | None = None

    def anchor_ledger_transaction(self, payload: AnchorPayload, *, idempotency_key: str) -> ProviderTransaction:
        self.payload = payload
        return ProviderTransaction(
            status="confirmed",
            transaction_hash="0x" + "ab" * 32,
            block_number=42,
            confirmed_at=datetime.now(timezone.utc),
        )

    def get_transaction(self, transaction_hash: str) -> ProviderTransaction | None:
        return None

    def verify_anchor(self, digest: str) -> ProviderAnchor | None:
        if self.payload is None:
            return None
        return ProviderAnchor(
            digest=digest,
            reference_id=f"0x{self.payload.reference_id.int:064x}",
            anchored_at=datetime.now(timezone.utc),
            submitter="local-test",
        )

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(status="available")


def test_product_create_retrieve_validation_and_organization_scope(payment_world: dict[str, Any]) -> None:
    client = _client(payment_world)
    payload = {
        "organization_id": str(payment_world["sender_organization_id"]),
        "sku": "PACK-100",
        "name": "Packaging unit",
        "description": "Industrial packaging unit",
        "category": "equipment",
        "quantity": "2.500",
        "unit": "piece",
    }
    created = client.post("/api/v1/products", headers=_headers(client), json=payload)
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]
    assert created.json()["quantity"] == "2.500"
    assert client.get(f"/api/v1/products/{product_id}").json()["sku"] == "PACK-100"
    assert client.post("/api/v1/products", headers=_headers(client), json=payload).status_code == 409
    assert client.post("/api/v1/products", headers=_headers(client), json={**payload, "quantity": "-1"}).status_code == 422
    outsider = payment_world["outsider"]
    assert isinstance(outsider, TestClient)
    assert outsider.get(f"/api/v1/products/{product_id}").status_code == 404
    assert outsider.get("/api/v1/products").json()["items"] == []


def test_asset_registration_ownership_history_and_internal_verification(payment_world: dict[str, Any]) -> None:
    client = _client(payment_world)
    created = _create_asset(client, payment_world)
    assert created.status_code == 201, created.text
    asset = created.json()
    asset_id = asset["id"]
    assert asset["current_owner_organization_id"] == str(payment_world["sender_organization_id"])
    assert asset["current_custodian_organization_id"] is None
    assert "metadata_json" not in asset
    history = client.get(f"/api/v1/assets/{asset_id}/history").json()["items"]
    ownership = client.get(f"/api/v1/assets/{asset_id}/ownership").json()["items"]
    verified = client.get(f"/api/v1/assets/{asset_id}/verify").json()
    assert [item["event_type"] for item in history] == ["REGISTERED"]
    assert history[0]["sequence_number"] == 1
    assert len(ownership) == 1
    assert verified["exists"] is True and verified["history_consistent"] is True
    assert verified["event_count"] == len(history)
    assert verified["blockchain_status"] == "NOT_ANCHORED"
    assert client.get(f"/api/v1/assets/{UUID(int=0)}").status_code == 404
    outsider = payment_world["outsider"]
    assert isinstance(outsider, TestClient)
    assert outsider.get(f"/api/v1/assets/{asset_id}").status_code == 404


def test_transfer_requires_a_valid_existing_account_number(payment_world: dict[str, Any]) -> None:
    client = _client(payment_world)
    created = _create_asset(client, payment_world, "MACHINE-ACCOUNT-LOOKUP")
    assert created.status_code == 201, created.text
    asset_id = created.json()["id"]
    url = f"/api/v1/assets/{asset_id}/transfer"
    invalid = client.post(
        url,
        headers=_headers(client, "asset-transfer-invalid-account"),
        json={"recipient_account_number": "not-an-account"},
    )
    unknown = client.post(
        url,
        headers=_headers(client, "asset-transfer-unknown-account"),
        json={"recipient_account_number": "000000000000000000"},
    )
    assert invalid.status_code == 422
    assert unknown.status_code == 404
    assert client.get(f"/api/v1/assets/{asset_id}").json()["current_owner_organization_id"] == str(
        payment_world["sender_organization_id"]
    )


def test_transfer_retry_history_and_cross_organization_access(payment_world: dict[str, Any]) -> None:
    client = _client(payment_world)
    created = _create_asset(client, payment_world)
    assert created.status_code == 201, created.text
    asset_id = created.json()["id"]
    url = f"/api/v1/assets/{asset_id}/transfer"
    payload = {"recipient_account_number": payment_world["recipient_account_number"]}
    first = client.post(url, headers=_headers(client, "asset-transfer-0001"), json=payload)
    retry = client.post(url, headers=_headers(client, "asset-transfer-0001"), json=payload)
    assert first.status_code == retry.status_code == 200
    assert first.json()["id"] == retry.json()["id"]
    assert first.json()["metadata"]["recipient_account_number"] == payment_world["recipient_account_number"]
    conflict = client.post(
        url,
        headers=_headers(client, "asset-transfer-0001"),
        json={"recipient_account_number": payment_world["sender_account_number"]},
    )
    assert conflict.status_code == 409
    events = client.get(f"/api/v1/assets/{asset_id}/history").json()["items"]
    owners = client.get(f"/api/v1/assets/{asset_id}/ownership").json()["items"]
    first_events = client.get(f"/api/v1/assets/{asset_id}/history?limit=1&offset=0").json()
    second_events = client.get(f"/api/v1/assets/{asset_id}/history?limit=1&offset=1").json()
    first_owners = client.get(f"/api/v1/assets/{asset_id}/ownership?limit=1&offset=0").json()
    second_owners = client.get(f"/api/v1/assets/{asset_id}/ownership?limit=1&offset=1").json()
    assert first_events["has_more"] is True
    assert [event["sequence_number"] for event in first_events["items"]] == [1]
    assert second_events["has_more"] is False
    assert [event["sequence_number"] for event in second_events["items"]] == [2]
    assert first_owners["has_more"] is True
    assert [item["organization_id"] for item in first_owners["items"]] == [str(payment_world["sender_organization_id"])]
    assert second_owners["has_more"] is False
    assert [item["organization_id"] for item in second_owners["items"]] == [str(payment_world["recipient_organization_id"])]
    assert [event["sequence_number"] for event in events] == [1, 2]
    assert [event["event_type"] for event in events] == ["REGISTERED", "TRANSFERRED"]
    assert [record["organization_id"] for record in owners] == [
        str(payment_world["sender_organization_id"]),
        str(payment_world["recipient_organization_id"]),
    ]
    assert client.get(f"/api/v1/assets/{asset_id}/verify").json()["history_consistent"] is True
    recipient = payment_world["recipient"]
    assert isinstance(recipient, TestClient)
    assert recipient.get(f"/api/v1/assets/{asset_id}").status_code == 200
    outsider = payment_world["outsider"]
    assert isinstance(outsider, TestClient)
    assert outsider.post(url, headers=_headers(outsider, "other-transfer-key"), json=payload).status_code == 404


def test_custody_retirement_and_lifecycle_rules(payment_world: dict[str, Any]) -> None:
    client = _client(payment_world)
    created = _create_asset(client, payment_world, "MACHINE-0002")
    assert created.status_code == 201
    asset_id = created.json()["id"]
    changed = client.post(
        f"/api/v1/assets/{asset_id}/custody",
        headers=_headers(client, "asset-custody-0001"),
        json={"custodian_account_number": payment_world["recipient_account_number"]},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["metadata"]["custodian_account_number"] == payment_world["recipient_account_number"]
    state = client.get(f"/api/v1/assets/{asset_id}").json()
    assert state["current_owner_organization_id"] == str(payment_world["sender_organization_id"])
    assert state["current_custodian_organization_id"] == str(payment_world["recipient_organization_id"])
    repeated_custody = client.post(
        f"/api/v1/assets/{asset_id}/custody",
        headers=_headers(client, "asset-custody-repeat-0001"),
        json={"custodian_account_number": payment_world["recipient_account_number"]},
    )
    assert repeated_custody.status_code == 409
    assert repeated_custody.json()["error"]["code"] == "CUSTODY_UNCHANGED"
    assert len(client.get(f"/api/v1/assets/{asset_id}/history").json()["items"]) == 2
    retired = client.post(
        f"/api/v1/assets/{asset_id}/retire",
        headers=_headers(client, "asset-retire-0001"),
        json={"status": "retired"},
    )
    assert retired.status_code == 200
    assert client.get(f"/api/v1/assets/{asset_id}").json()["status"] == "retired"
    rejected = client.post(
        f"/api/v1/assets/{asset_id}/transfer",
        headers=_headers(client, "asset-transfer-retired"),
        json={"recipient_account_number": payment_world["recipient_account_number"]},
    )
    assert rejected.status_code == 409
    assert [event["event_type"] for event in client.get(f"/api/v1/assets/{asset_id}/history").json()["items"]] == [
        "REGISTERED", "CUSTODY_CHANGED", "RETIRED"
    ]
    assert client.get(f"/api/v1/assets/{asset_id}/verify").json()["history_consistent"] is True


def test_owner_role_csrf_and_metadata_validation(payment_world: dict[str, Any]) -> None:
    client = _client(payment_world)
    asset = _create_asset(client, payment_world, "MACHINE-0003")
    assert asset.status_code == 201
    asset_id = asset.json()["id"]
    no_csrf = client.post(
        f"/api/v1/assets/{asset_id}/custody",
        json={"custodian_account_number": payment_world["recipient_account_number"]},
    )
    assert no_csrf.status_code == 403
    database = payment_world["database"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        membership = session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == UUID(str(payment_world["sender_user_id"]))
            )
        )
        assert membership is not None
        membership.role = "member"
        session.commit()
    denied = client.post(
        f"/api/v1/assets/{asset_id}/transfer",
        headers=_headers(client, "asset-transfer-member"),
        json={"recipient_account_number": payment_world["recipient_account_number"]},
    )
    denied_custody = client.post(
        f"/api/v1/assets/{asset_id}/custody",
        headers=_headers(client, "asset-custody-member"),
        json={"custodian_account_number": payment_world["recipient_account_number"]},
    )
    denied_retirement = client.post(
        f"/api/v1/assets/{asset_id}/retire",
        headers=_headers(client, "asset-retire-member"),
        json={"status": "retired"},
    )
    assert denied.status_code == denied_custody.status_code == denied_retirement.status_code == 403
    invalid = client.post(
        "/api/v1/assets",
        headers=_headers(client),
        json={
            "organization_id": str(payment_world["sender_organization_id"]),
            "asset_identifier": "BAD-METADATA",
            "category": "other",
            "name": "Bad metadata",
            "metadata": {"payload": "x" * 9000},
        },
    )
    assert invalid.status_code == 422


def test_simulated_anchor_is_not_reported_as_confirmed(payment_world: dict[str, Any]) -> None:
    client = _client(payment_world)
    created = _create_asset(client, payment_world, "MACHINE-0004")
    assert created.status_code == 201
    asset_id = created.json()["id"]
    event = client.get(f"/api/v1/assets/{asset_id}/history").json()["items"][0]
    anchored = client.post(
        f"/api/v1/assets/{asset_id}/history/{event['id']}/anchor", headers=_headers(client)
    )
    assert anchored.status_code == 200, anchored.text
    assert anchored.json()["asset_event_id"] == event["id"]
    assert anchored.json()["ledger_transaction_id"] is None
    assert anchored.json()["digest_version"] == "ledgerchain-asset-event-v1"
    assert anchored.json()["status"] == "simulated"
    verification = client.get(f"/api/v1/assets/{asset_id}/verify").json()
    assert verification["blockchain_status"] == "SIMULATED"
    assert verification["integrity_warning"] is False
    activity = client.get("/api/v1/activity?type=blockchain").json()["items"]
    assert len(activity) == 1
    assert activity[0]["anchor_status"] == "simulated"
    assert activity[0]["asset_event_id"] == event["id"]
    assert activity[0]["transaction_hash"] is None and activity[0]["block_number"] is None
    database = payment_world["database"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        assert len(session.scalars(select(BlockchainRecord).where(BlockchainRecord.asset_event_id == UUID(event["id"]))).all()) == 1


def test_asset_anchor_match_and_tamper_mismatch(payment_world: dict[str, Any]) -> None:
    client = _client(payment_world)
    created = _create_asset(client, payment_world, "MACHINE-0005")
    assert created.status_code == 201
    event_id = UUID(client.get(f"/api/v1/assets/{created.json()['id']}/history").json()["items"][0]["id"])
    database = payment_world["database"]
    assert isinstance(database, Database)
    provider = ConfirmingAssetProvider()
    with database.session_factory() as session:
        user = session.get(User, UUID(str(payment_world["sender_user_id"])))
        assert user is not None
        service = BlockchainService(
            session,
            Settings(_env_file=None, environment="test", blockchain_enabled=True),
            provider=provider,
        )
        record = service.anchor_asset_event(event_id, user)
        assert record.status == "confirmed" and record.asset_event_id == event_id
        assert service.verify_asset_event(event_id, user)["blockchain_status"] == "ANCHORED_MATCH"
        event = session.get(AssetEvent, event_id)
        assert event is not None
        event.resulting_state = {"owner": "tampered", "custodian": None, "status": "active"}
        session.commit()
        result = service.verify_asset_event(event_id, user)
        assert result["blockchain_status"] == "ANCHORED_MISMATCH"
        assert result["integrity_warning"] is True


def test_failed_transfer_rolls_back_asset_and_event(payment_world: dict[str, Any]) -> None:
    client = _client(payment_world)
    created = _create_asset(client, payment_world, "MACHINE-0006")
    assert created.status_code == 201, created.text
    asset_id = created.json()["id"]
    database = payment_world["database"]
    assert isinstance(database, Database)
    with database.engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TRIGGER force_asset_event_failure BEFORE INSERT ON asset_events "
            "WHEN NEW.event_type = 'TRANSFERRED' BEGIN "
            "SELECT RAISE(ABORT, 'forced asset event failure'); END"
        )
    response = client.post(
        f"/api/v1/assets/{asset_id}/transfer",
        headers=_headers(client, "asset-transfer-rollback"),
        json={"recipient_account_number": payment_world["recipient_account_number"]},
    )
    assert response.status_code == 409
    assert client.get(f"/api/v1/assets/{asset_id}").json()["current_owner_organization_id"] == str(
        payment_world["sender_organization_id"]
    )
    assert [event["event_type"] for event in client.get(f"/api/v1/assets/{asset_id}/history").json()["items"]] == [
        "REGISTERED"
    ]
    with database.session_factory() as session:
        assert len(session.scalars(select(AssetOwnership).where(AssetOwnership.asset_id == UUID(asset_id))).all()) == 1


