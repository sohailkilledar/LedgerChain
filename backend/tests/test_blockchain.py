
import pytest

pytestmark = pytest.mark.skip(
    reason='Blockchain anchoring and verification logic is intentionally excluded from this public source distribution.',
)

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from app.blockchain.development import DevelopmentBlockchainProvider
from app.blockchain.provider import AnchorPayload, BlockchainProviderError, ProviderHealth, ProviderTransaction
from app.core.config import Settings
from app.core.errors import ConflictError, ServiceUnavailableError
from app.db.session import Database
from app.models.auth import User
from app.models.blockchain import BlockchainRecord
from app.models.ledger import LedgerTransaction
from app.services.blockchain import BlockchainService, DIGEST_VERSION, ledger_digest
from tests.test_payments import _headers, _transfer, payment_world


class PendingProvider:
    provider_id = "test-provider"
    network = "test-network"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.submissions: list[tuple[AnchorPayload, str]] = []
        self.lookups = 0

    def anchor_ledger_transaction(self, payload: AnchorPayload, *, idempotency_key: str) -> ProviderTransaction:
        self.submissions.append((payload, idempotency_key))
        if self.fail:
            raise RuntimeError("rpc token must never be logged or returned")
        return ProviderTransaction(
            status="submitted",
            transaction_hash="test-transaction-hash",
            submitted_at=datetime.now(timezone.utc),
        )

    def get_transaction(self, transaction_hash: str) -> ProviderTransaction:
        self.lookups += 1
        return ProviderTransaction(
            status="confirmed",
            transaction_hash=transaction_hash,
            block_number=17,
            submitted_at=datetime.now(timezone.utc),
            confirmed_at=datetime.now(timezone.utc),
        )

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(status="available")


def _ledger_transaction(world: dict[str, Any], payment_response: Any) -> UUID:
    database = world["database"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        transaction = session.scalar(
            select(LedgerTransaction).where(LedgerTransaction.reference == payment_response.json()["reference"])
        )
        assert transaction is not None
        return transaction.id


def test_development_anchor_is_simulated_and_idempotent(payment_world: dict[str, Any]) -> None:
    payment = _transfer(payment_world)
    assert payment.status_code == 201, payment.text
    ledger_id = _ledger_transaction(payment_world, payment)
    sender = payment_world["sender"]
    assert isinstance(sender, TestClient)

    first = sender.post(f"/api/v1/blockchain/ledger/{ledger_id}/anchor", headers=_headers(sender))
    second = sender.post(f"/api/v1/blockchain/ledger/{ledger_id}/anchor", headers=_headers(sender))
    assert first.status_code == second.status_code == 200
    record = first.json()
    assert second.json()["id"] == record["id"]
    assert record["ledger_transaction_id"] == str(ledger_id)
    assert record["provider"] == "development"
    assert record["status"] == "simulated"
    assert record["transaction_hash"] is None
    assert record["block_number"] is None
    assert len(record["digest"]) == 64
    assert record["digest_version"] == DIGEST_VERSION

    verification = sender.get(f"/api/v1/blockchain/ledger/{ledger_id}/verify")
    assert verification.status_code == 200
    assert verification.json()["result"] == "NOT_ANCHORED"
    assert verification.json()["integrity_warning"] is False

    database = payment_world["database"]
    with database.session_factory() as session:
        assert len(session.scalars(select(BlockchainRecord)).all()) == 1

    lookup = sender.get(f"/api/v1/blockchain/transactions/{record['id']}")
    assert lookup.status_code == 200
    assert lookup.json()["status"] == "simulated"
    status = sender.get("/api/v1/blockchain/status")
    assert status.status_code == 200
    assert status.json()["health"] == "simulated"


def test_protected_api_hides_unauthorized_ledger_and_rejects_anonymous_requests(
    payment_world: dict[str, Any],
) -> None:
    payment = _transfer(payment_world)
    ledger_id = _ledger_transaction(payment_world, payment)
    outsider = payment_world["outsider"]
    assert isinstance(outsider, TestClient)
    denied = outsider.post(f"/api/v1/blockchain/ledger/{ledger_id}/anchor", headers=_headers(outsider))
    assert denied.status_code == 404
    verify_denied = outsider.get(f"/api/v1/blockchain/ledger/{ledger_id}/verify")
    assert verify_denied.status_code == 404

    sender = payment_world["sender"]
    assert isinstance(sender, TestClient)
    anonymous = TestClient(sender.app, raise_server_exceptions=False)
    response = anonymous.post(f"/api/v1/blockchain/ledger/{ledger_id}/anchor")
    assert response.status_code == 401
    assert anonymous.get("/api/v1/blockchain/status").status_code == 401

    arbitrary = sender.post("/api/v1/blockchain/send-raw-transaction", headers=_headers(sender), json={"data": "x"})
    assert arbitrary.status_code == 404


def test_provider_pending_then_confirmation_is_persisted(payment_world: dict[str, Any]) -> None:
    payment = _transfer(payment_world)
    ledger_id = _ledger_transaction(payment_world, payment)
    database = payment_world["database"]
    provider = PendingProvider()
    user_id = payment_world["sender_user_id"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        user = session.get(User, user_id)
        assert user is not None
        settings = Settings(_env_file=None, environment="test", blockchain_enabled=True)
        service = BlockchainService(session, settings, provider)
        submitted = service.anchor(ledger_id, user)
        assert submitted.status == "submitted"
        assert submitted.transaction_hash == "test-transaction-hash"
        assert submitted.confirmed_at is None
        assert provider.submissions[0][1] == str(submitted.id)

        repeated = service.anchor(ledger_id, user)
        assert repeated.id == submitted.id
        assert len(provider.submissions) == 1
        confirmed = service.get_record(submitted.id, user)
        assert confirmed.status == "confirmed"
        assert confirmed.block_number == 17
        assert confirmed.confirmed_at is not None
        assert provider.lookups == 1


def test_provider_failure_is_stored_safely_and_retry_is_idempotent(
    payment_world: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    payment = _transfer(payment_world)
    ledger_id = _ledger_transaction(payment_world, payment)
    database = payment_world["database"]
    provider = PendingProvider(fail=True)
    user_id = payment_world["sender_user_id"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        user = session.get(User, user_id)
        assert user is not None
        settings = Settings(_env_file=None, environment="test", blockchain_enabled=True)
        service = BlockchainService(session, settings, provider)
        failed = service.anchor(ledger_id, user)
        assert failed.status == "submission_failed"
        assert failed.failure_code == "PROVIDER_SUBMISSION_FAILED"
        assert failed.transaction_hash is None
        assert "rpc token" not in caplog.text

        provider.fail = False
        retried = service.anchor(ledger_id, user)
        assert retried.status == "submitted"
        assert retried.id == failed.id
        assert len(provider.submissions) == 2
        assert provider.submissions[0][1] == provider.submissions[1][1]


def test_provider_timeout_is_a_retryable_record_state(payment_world: dict[str, Any]) -> None:
    payment = _transfer(payment_world)
    ledger_id = _ledger_transaction(payment_world, payment)
    database = payment_world["database"]
    assert isinstance(database, Database)

    class TimeoutProvider(PendingProvider):
        def anchor_ledger_transaction(self, payload: AnchorPayload, *, idempotency_key: str) -> ProviderTransaction:
            raise BlockchainProviderError("PROVIDER_TIMEOUT")

    with database.session_factory() as session:
        user = session.get(User, payment_world["sender_user_id"])
        assert user is not None
        service = BlockchainService(
            session,
            Settings(_env_file=None, environment="test", blockchain_enabled=True),
            TimeoutProvider(),
        )
        failed = service.anchor(ledger_id, user)
        assert failed.status == "submission_failed"
        assert failed.failure_code == "PROVIDER_TIMEOUT"
        assert failed.transaction_hash is None


def test_disabled_provider_does_not_create_an_anchor(payment_world: dict[str, Any]) -> None:
    payment = _transfer(payment_world)
    ledger_id = _ledger_transaction(payment_world, payment)
    database = payment_world["database"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        user = session.get(User, payment_world["sender_user_id"])
        assert user is not None
        service = BlockchainService(
            session,
            Settings(_env_file=None, environment="test", blockchain_enabled=False),
        )
        with pytest.raises(ServiceUnavailableError) as error:
            service.anchor(ledger_id, user)
        assert error.value.code == "BLOCKCHAIN_DISABLED"
        assert service.status().health == "disabled"
        assert session.scalar(select(BlockchainRecord)) is None


def test_unimplemented_provider_configuration_reports_unavailable(payment_world: dict[str, Any]) -> None:
    payment = _transfer(payment_world)
    ledger_id = _ledger_transaction(payment_world, payment)
    database = payment_world["database"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        user = session.get(User, payment_world["sender_user_id"])
        assert user is not None
        settings = Settings(
            _env_file=None,
            environment="test",
            blockchain_provider="future-provider",
            blockchain_network="future-testnet",
        )
        service = BlockchainService(session, settings)
        assert service.status().health == "unavailable"
        result = service.anchor(ledger_id, user)
        assert result.provider == "future-provider"
        assert result.network == "future-testnet"
        assert result.status == "submission_failed"
        assert result.failure_code == "PROVIDER_UNAVAILABLE"
        assert result.transaction_hash is None


def test_provider_interface_and_development_health_are_explicit() -> None:
    provider = DevelopmentBlockchainProvider("local-simulation")
    response = provider.anchor_ledger_transaction(
        AnchorPayload(UUID(int=1), DIGEST_VERSION, "a" * 64), idempotency_key="record-id"
    )
    assert response.status == "simulated"
    assert response.transaction_hash is None
    assert provider.health_check().status == "simulated"


def test_simulated_result_cannot_contain_real_chain_details(payment_world: dict[str, Any]) -> None:
    database = payment_world["database"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        service = BlockchainService(
            session,
            Settings(_env_file=None, environment="test"),
        )
        record = BlockchainRecord(status="submitting")
        with pytest.raises(BlockchainProviderError) as error:
            service._apply_provider_result(
                record,
                ProviderTransaction(status="simulated", transaction_hash="not-a-real-hash"),
            )
        assert error.value.code == "PROVIDER_INVALID_RESPONSE"


def test_invalid_state_transition_is_rejected() -> None:
    record = BlockchainRecord(status="confirmed")
    with pytest.raises(ConflictError) as error:
        BlockchainService.transition(record, "submitting")
    assert error.value.code == "INVALID_BLOCKCHAIN_STATE"


def test_digest_is_deterministic_and_changes_when_ledger_changes() -> None:
    transaction = SimpleNamespace(
        id=UUID(int=1),
        reference="LC-LEDGER-1",
        transaction_type="payment_transfer",
        currency="INR",
        amount=Decimal("12.50"),
        posted_at=datetime(2026, 9, 27, tzinfo=timezone.utc),
    )
    debit = SimpleNamespace(direction="debit", amount=Decimal("12.50"), currency="INR")
    credit = SimpleNamespace(direction="credit", amount=Decimal("12.50"), currency="INR")
    original = ledger_digest(transaction, [debit, credit])
    assert original == ledger_digest(transaction, [credit, debit])
    changed = SimpleNamespace(direction="credit", amount=Decimal("12.51"), currency="INR")
    assert original != ledger_digest(transaction, [debit, changed])


def test_provider_error_codes_are_sanitized() -> None:
    error = BlockchainProviderError("rpc-secret-url-and-token")
    assert error.code == "PROVIDER_SUBMISSION_FAILED"
    assert "rpc-secret" not in str(error)
