
import pytest

pytestmark = pytest.mark.skip(
    reason='Payment execution logic is intentionally excluded from this public source distribution.',
)

from collections.abc import Iterator
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.errors import ConflictError
from app.models.ledger import LedgerEntry, LedgerTransaction
from app.repositories.ledger import LedgerRepository
from app.services.ledger import LedgerService
from app.db.base import Base
from app.db.session import Database, create_session_factory
from app.main import create_app
from app.models.account import Organization, OrganizationMembership
from app.models.payment import Payment
from app.repositories.payment import PaymentAccountRepository, PaymentRepository
from app.services.payment import PaymentService

PASSWORD = "LedgerChain1!"


@pytest.fixture
def payment_world() -> Iterator[dict[str, object]]:
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
        sender_user_id, sender_account = _register_and_login(sender, "sender@example.com")
        recipient_user_id, recipient_account = _register_and_login(recipient, "recipient@example.com")
        outsider_user_id, _ = _register_and_login(outsider, "outsider@example.com")
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
            sender_organization.balance = 1000
            recipient_organization.name = "Recipient Trading"
            session.commit()
        yield {
            "database": database,
            "sender": sender,
            "recipient": recipient,
            "outsider": outsider,
            "sender_user_id": sender_user_id,
            "recipient_user_id": recipient_user_id,
            "outsider_user_id": outsider_user_id,
            "sender_account": sender_account,
            "recipient_account": recipient_account,
            "sender_organization_id": sender_membership.organization_id,
            "recipient_organization_id": recipient_membership.organization_id,
        }
    database.dispose()


def _register_and_login(client: TestClient, email: str) -> tuple[UUID, dict[str, object]]:
    registered = client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})
    assert registered.status_code == 201, registered.text
    logged_in = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert logged_in.status_code == 200, logged_in.text
    account = client.get("/api/v1/account")
    assert account.status_code == 200, account.text
    return UUID(logged_in.json()["user"]["id"]), account.json()


def _headers(client: TestClient, idempotency_key: str = "payment-test-key-001") -> dict[str, str]:
    csrf_token = client.cookies.get("ledgerchain_csrf")
    assert csrf_token
    return {"X-CSRF-Token": csrf_token, "Idempotency-Key": idempotency_key}


def _payload(recipient_account: str, amount: str = "100.00") -> dict[str, object]:
    return {
        "recipient_account": recipient_account,
        "amount": amount,
        "currency": "INR",
        "purpose": "invoice",
        "note": "Invoice #42",
    }


def _transfer(world: dict[str, object], *, amount: str = "100.00", key: str = "payment-test-key-001"):
    sender = world["sender"]
    assert isinstance(sender, TestClient)
    account = world["recipient_account"]
    assert isinstance(account, dict)
    return sender.post(
        "/api/v1/payments",
        headers=_headers(sender, key),
        json=_payload(str(account["account_number"]), amount),
    )


def test_payment_debits_and_credits_atomically_with_reference_and_zero_fee(payment_world: dict[str, object]) -> None:
    response = _transfer(payment_world, amount="1000.00")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["amount"] == "1000.00"
    assert body["fee"] == "0.00"
    assert body["total_debit"] == "1000.00"
    assert body["sender_account"] == payment_world["sender_account"]["account_number"]
    assert body["recipient_name"] == "Recipient Trading"
    assert body["reference"].startswith("LC-PAY-")
    assert body["completed_at"] is not None

    database = payment_world["database"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        sender = session.get(Organization, payment_world["sender_organization_id"])
        recipient = session.get(Organization, payment_world["recipient_organization_id"])
        assert sender is not None and sender.balance == 0
        assert recipient is not None and recipient.balance == 1000
        assert session.scalar(select(Payment).where(Payment.reference == body["reference"])) is not None


def test_idempotency_replays_without_second_debit_and_rejects_conflicting_reuse(
    payment_world: dict[str, object],
) -> None:
    first = _transfer(payment_world, amount="100.00", key="retry-key-0001")
    second = _transfer(payment_world, amount="100.00", key="retry-key-0001")
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    conflict = _transfer(payment_world, amount="101.00", key="retry-key-0001")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert conflict.json()["error"]["committed"] is False

    database = payment_world["database"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        assert len(session.scalars(select(Payment)).all()) == 1
        sender = session.get(Organization, payment_world["sender_organization_id"])
        recipient = session.get(Organization, payment_world["recipient_organization_id"])
        assert sender is not None and sender.balance == 900
        assert recipient is not None and recipient.balance == 100


def test_insufficient_balance_is_non_committed_and_exact_balance_succeeds(
    payment_world: dict[str, object],
) -> None:
    too_much = _transfer(payment_world, amount="1000.01", key="insufficient-key-01")
    assert too_much.status_code == 409
    assert too_much.json()["error"]["code"] == "INSUFFICIENT_BALANCE"
    assert too_much.json()["error"]["committed"] is False

    exact = _transfer(payment_world, amount="1000.00", key="exact-balance-key-01")
    assert exact.status_code == 201
    database = payment_world["database"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        sender = session.get(Organization, payment_world["sender_organization_id"])
        assert sender is not None and sender.balance == 0


@pytest.mark.parametrize("amount", ["0", "-1", "1.001", "NaN", 10.25, "1e2"])
def test_invalid_amounts_are_rejected_without_mutating_balances(
    payment_world: dict[str, object], amount: object
) -> None:
    sender = payment_world["sender"]
    assert isinstance(sender, TestClient)
    recipient_account = payment_world["recipient_account"]
    assert isinstance(recipient_account, dict)
    response = sender.post(
        "/api/v1/payments",
        headers=_headers(sender, "invalid-amount-key-001"),
        json={**_payload(str(recipient_account["account_number"])), "amount": amount},
    )
    assert response.status_code == 422
    database = payment_world["database"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        assert session.scalar(select(Payment)) is None
        sender_account = session.get(Organization, payment_world["sender_organization_id"])
        assert sender_account is not None and sender_account.balance == 1000


@pytest.mark.parametrize(
    ("field", "value"),
    [("currency", "USD"), ("purpose", "tax"), ("note", "x" * 141)],
)
def test_currency_purpose_and_note_constraints_are_enforced(
    payment_world: dict[str, object], field: str, value: str
) -> None:
    sender = payment_world["sender"]
    recipient_account = payment_world["recipient_account"]
    assert isinstance(sender, TestClient) and isinstance(recipient_account, dict)
    response = sender.post(
        "/api/v1/payments",
        headers=_headers(sender, "constraint-validation-key"),
        json={**_payload(str(recipient_account["account_number"])), field: value},
    )
    assert response.status_code == 422


def test_recipient_self_transfer_missing_fields_and_sender_override_are_rejected(
    payment_world: dict[str, object],
) -> None:
    sender = payment_world["sender"]
    assert isinstance(sender, TestClient)
    own_account = payment_world["sender_account"]
    recipient_account = payment_world["recipient_account"]
    assert isinstance(own_account, dict) and isinstance(recipient_account, dict)

    self_transfer = sender.post(
        "/api/v1/payments",
        headers=_headers(sender, "self-payment-key-001"),
        json=_payload(str(own_account["account_number"])),
    )
    missing = sender.post(
        "/api/v1/payments",
        headers=_headers(sender, "missing-fields-key-01"),
        json={"recipient_account": recipient_account["account_number"], "amount": "1.00"},
    )
    sender_override = sender.post(
        "/api/v1/payments",
        headers=_headers(sender, "sender-override-key-01"),
        json={**_payload(str(recipient_account["account_number"])), "sender_account": own_account["account_number"]},
    )
    assert self_transfer.status_code == 422
    assert missing.status_code == sender_override.status_code == 422

    unknown = sender.post(
        "/api/v1/payments",
        headers=_headers(sender, "unknown-recipient-key"),
        json=_payload("999999999999999999"),
    )
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "RECIPIENT_NOT_FOUND"


def test_payment_authentication_and_csrf_are_required(payment_world: dict[str, object]) -> None:
    app = payment_world["sender"].app
    anonymous = TestClient(app, raise_server_exceptions=False)
    response = anonymous.post(
        "/api/v1/payments",
        headers={"Idempotency-Key": "anonymous-payment-key"},
        json=_payload(str(payment_world["recipient_account"]["account_number"])),
    )
    assert response.status_code == 401
    assert anonymous.get("/api/v1/payments").status_code == 401
    sender = payment_world["sender"]
    assert isinstance(sender, TestClient)
    no_csrf = sender.post(
        "/api/v1/payments",
        headers={"Idempotency-Key": "missing-csrf-payment-key"},
        json=_payload(str(payment_world["recipient_account"]["account_number"])),
    )
    assert no_csrf.status_code == 403
    anonymous.close()


def test_payment_read_access_and_pagination_are_scoped_to_parties(payment_world: dict[str, object]) -> None:
    created = _transfer(payment_world)
    assert created.status_code == 201, created.text
    payment_id = created.json()["id"]
    recipient = payment_world["recipient"]
    outsider = payment_world["outsider"]
    sender = payment_world["sender"]
    assert isinstance(recipient, TestClient) and isinstance(outsider, TestClient) and isinstance(sender, TestClient)

    assert sender.get(f"/api/v1/payments/{payment_id}").status_code == 200
    assert recipient.get(f"/api/v1/payments/{payment_id}").status_code == 200
    hidden = outsider.get(f"/api/v1/payments/{payment_id}")
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "PAYMENT_NOT_FOUND"
    assert len(sender.get("/api/v1/payments?limit=1&offset=0").json()["items"]) == 1
    assert len(recipient.get("/api/v1/payments").json()["items"]) == 1
    assert outsider.get("/api/v1/payments").json()["items"] == []
    assert sender.get("/api/v1/payments?limit=0").status_code == 422


def test_processing_failure_rolls_back_both_balances_and_payment(
    payment_world: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    def flush_then_fail(repository: PaymentRepository, payment: Payment) -> Payment:
        repository.session.add(payment)
        repository.session.flush()
        raise RuntimeError("simulated database-stage failure")

    monkeypatch.setattr(PaymentRepository, "add", flush_then_fail)
    response = _transfer(payment_world)
    assert response.status_code == 500
    assert response.json()["error"]["committed"] is False
    database = payment_world["database"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        sender = session.get(Organization, payment_world["sender_organization_id"])
        recipient = session.get(Organization, payment_world["recipient_organization_id"])
        assert sender is not None and sender.balance == 1000
        assert recipient is not None and recipient.balance == 0
        assert session.scalar(select(Payment)) is None


def test_invalid_payment_state_transitions_are_rejected(payment_world: dict[str, object]) -> None:
    payment = Payment(status="pending")
    service = PaymentService(payment_world["database"].session_factory())
    service.transition(payment, "processing")
    service.transition(payment, "completed")
    with pytest.raises(ConflictError) as error:
        service.transition(payment, "processing")
    assert error.value.code == "INVALID_PAYMENT_STATE"
    service.session.close()


def test_completed_payment_posts_balanced_ledger_and_activity_is_scoped(payment_world: dict[str, object]) -> None:
    created = _transfer(payment_world, amount="123.45", key="ledger-posting-key-001")
    assert created.status_code == 201, created.text
    payment_id = created.json()["id"]
    sender = payment_world["sender"]
    recipient = payment_world["recipient"]
    outsider = payment_world["outsider"]
    assert isinstance(sender, TestClient) and isinstance(recipient, TestClient) and isinstance(outsider, TestClient)

    database = payment_world["database"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        transaction = session.scalar(select(LedgerTransaction).where(LedgerTransaction.payment_id == UUID(payment_id)))
        assert transaction is not None
        assert transaction.status == "posted"
        assert transaction.amount == Decimal("123.45")
        assert transaction.posted_at is not None
        entries = list(
            session.scalars(
                select(LedgerEntry).where(LedgerEntry.ledger_transaction_id == transaction.id)
            ).all()
        )
        assert len(entries) == 2
        debits = [entry for entry in entries if entry.direction == "debit"]
        credits = [entry for entry in entries if entry.direction == "credit"]
        assert len(debits) == len(credits) == 1
        assert debits[0].account_id == payment_world["sender_organization_id"]
        assert credits[0].account_id == payment_world["recipient_organization_id"]
        assert debits[0].amount == credits[0].amount == Decimal("123.45")

    sender_activity = sender.get("/api/v1/activity?type=payment&limit=1").json()
    recipient_activity = recipient.get("/api/v1/activity").json()
    assert sender_activity["items"][0]["direction"] == "outgoing"
    assert sender_activity["items"][0]["title"] == "Payment sent"
    assert sender_activity["items"][0]["payment_id"] == payment_id
    assert sender_activity["items"][0]["ledger_transaction_id"] == str(transaction.id)
    assert recipient_activity["items"][0]["direction"] == "incoming"
    assert recipient_activity["items"][0]["counterparty"] == "My organization"
    assert outsider.get("/api/v1/activity").json()["items"] == []
    assert sender.get("/api/v1/activity?limit=0").status_code == 422
    assert sender.get("/api/v1/activity?type=loan").status_code == 422
    anonymous = TestClient(sender.app, raise_server_exceptions=False)
    assert anonymous.get("/api/v1/activity").status_code == 401
    anonymous.close()

    ledger_url = f"/api/v1/ledger/{transaction.id}"
    ledger_response = sender.get(ledger_url)
    assert ledger_response.status_code == 200
    assert len(ledger_response.json()["entries"]) == 2
    assert recipient.get(ledger_url).status_code == 200
    hidden = outsider.get(ledger_url)
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "LEDGER_TRANSACTION_NOT_FOUND"
    assert sender.patch(ledger_url, json={"amount": "1.00"}).status_code == 405
    assert sender.delete(ledger_url).status_code == 405


def test_activity_pagination_is_chronological_and_has_more(payment_world: dict[str, object]) -> None:
    first = _transfer(payment_world, amount="25.00", key="activity-page-key-001")
    second = _transfer(payment_world, amount="30.00", key="activity-page-key-002")
    assert first.status_code == second.status_code == 201
    sender = payment_world["sender"]
    assert isinstance(sender, TestClient)

    first_page = sender.get("/api/v1/activity?limit=1&offset=0")
    second_page = sender.get("/api/v1/activity?limit=1&offset=1")
    assert first_page.status_code == second_page.status_code == 200
    assert len(first_page.json()["items"]) == len(second_page.json()["items"]) == 1
    assert first_page.json()["has_more"] is True
    assert second_page.json()["has_more"] is False
    assert first_page.json()["items"][0]["timestamp"] >= second_page.json()["items"][0]["timestamp"]
    assert first_page.json()["items"][0]["payment_id"] != second_page.json()["items"][0]["payment_id"]


def test_payment_retry_does_not_duplicate_ledger_transaction(payment_world: dict[str, object]) -> None:
    first = _transfer(payment_world, amount="100.00", key="ledger-retry-key-001")
    second = _transfer(payment_world, amount="100.00", key="ledger-retry-key-001")
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    database = payment_world["database"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        assert len(session.scalars(select(LedgerTransaction)).all()) == 1
        assert len(session.scalars(select(LedgerEntry)).all()) == 2


def test_ledger_integrity_failure_rolls_back_payment_balances_and_entries(
    payment_world: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    def unbalanced_totals(repository: LedgerRepository, transaction_id: UUID):
        return 1, 1, 100, 99

    monkeypatch.setattr(LedgerRepository, "balanced_totals", unbalanced_totals)
    response = _transfer(payment_world, amount="100.00", key="ledger-rollback-key-01")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "LEDGER_INTEGRITY_ERROR"
    assert response.json()["error"]["committed"] is False

    database = payment_world["database"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        sender = session.get(Organization, payment_world["sender_organization_id"])
        recipient = session.get(Organization, payment_world["recipient_organization_id"])
        assert sender is not None and sender.balance == 1000
        assert recipient is not None and recipient.balance == 0
        assert session.scalar(select(Payment)) is None
        assert session.scalar(select(LedgerTransaction)) is None
        assert session.scalar(select(LedgerEntry)) is None


def test_account_balance_lock_compiles_to_postgresql_for_update(payment_world: dict[str, object]) -> None:
    database = payment_world["database"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        repository = PaymentAccountRepository(session)
        statement = repository.lock_statement([payment_world["sender_organization_id"]])
        assert "FOR UPDATE" in str(statement.compile(dialect=postgresql.dialect()))
        assert repository.lock_accounts([payment_world["sender_organization_id"]])
