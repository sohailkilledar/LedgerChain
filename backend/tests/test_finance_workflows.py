
import pytest

pytestmark = pytest.mark.skip(
    reason='Finance mutation workflows are intentionally excluded from this public source distribution.',
)

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base
from app.db.session import Database, create_session_factory
from app.main import create_app
from app.models.account import Organization, OrganizationMembership
from app.models.ledger import LedgerEntry, LedgerTransaction
from app.models.payment import Payment

PASSWORD = "LedgerChain1!"


@pytest.fixture
def finance_world() -> Iterator[dict[str, object]]:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    database = Database(engine=engine, session_factory=create_session_factory(engine))
    app = create_app(Settings(_env_file=None, environment="test", cors_origins="http://localhost:3000"), database)
    with TestClient(app, raise_server_exceptions=False) as requester, TestClient(app, raise_server_exceptions=False) as recipient, TestClient(app, raise_server_exceptions=False) as approver:
        requester_user, requester_account = _register(requester, "requester@example.com")
        _, recipient_account = _register(recipient, "recipient@example.com")
        approver_user, _ = _register(approver, "approver@example.com")
        with database.session_factory() as session:
            requester_member = session.scalar(select(OrganizationMembership).where(OrganizationMembership.user_id == requester_user))
            assert requester_member is not None
            requester_member.role = "member"
            session.add(OrganizationMembership(organization_id=requester_member.organization_id, user_id=approver_user, role="owner"))
            sender_org = session.get(Organization, requester_member.organization_id)
            assert sender_org is not None
            sender_org.balance = Decimal("5000.00")
            session.commit()
        yield {
            "database": database,
            "requester": requester,
            "recipient": recipient,
            "approver": approver,
            "organization_id": requester_account["id"],
            "recipient_account": recipient_account["account_number"],
        }
    database.dispose()


def _register(client: TestClient, email: str) -> tuple[UUID, dict[str, object]]:
    registered = client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})
    assert registered.status_code == 201, registered.text
    logged_in = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert logged_in.status_code == 200, logged_in.text
    return UUID(logged_in.json()["user"]["id"]), client.get("/api/v1/account").json()


def _headers(client: TestClient, key: str = "finance-test-key") -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies["ledgerchain_csrf"], "Idempotency-Key": key}


def _create_request(world: dict[str, object], *, amount: str = "100.00", key: str = "finance-request-key", budget_id: str | None = None):
    requester = world["requester"]
    assert isinstance(requester, TestClient)
    payload: dict[str, object] = {
        "organization_id": world["organization_id"],
        "recipient_account": world["recipient_account"],
        "amount": amount,
        "purpose": "supplier",
        "note": "September restock",
    }
    if budget_id:
        payload["budget_id"] = budget_id
    return requester.post("/api/v1/finance/payment-requests", headers=_headers(requester, key), json=payload)


def _make_submitted_request(world: dict[str, object], *, amount: str = "100.00", key: str = "finance-request-key", budget_id: str | None = None) -> str:
    created = _create_request(world, amount=amount, key=key, budget_id=budget_id)
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]
    requester = world["requester"]
    assert isinstance(requester, TestClient)
    submitted = requester.post(f"/api/v1/finance/payment-requests/{request_id}/submit", headers=_headers(requester))
    replay = requester.post(f"/api/v1/finance/payment-requests/{request_id}/submit", headers=_headers(requester))
    assert submitted.status_code == replay.status_code == 200, submitted.text
    assert replay.json()["status"] == "SUBMITTED"
    return request_id


def test_budgeted_request_approval_execution_posts_payment_and_ledger(finance_world: dict[str, object]) -> None:
    approver = finance_world["approver"]
    requester = finance_world["requester"]
    database = finance_world["database"]
    assert isinstance(approver, TestClient) and isinstance(requester, TestClient) and isinstance(database, Database)
    today = date.today()
    budget = approver.post("/api/v1/finance/budgets", headers=_headers(approver), json={
        "organization_id": finance_world["organization_id"], "name": "Supplier purchases", "category": "supplier",
        "period_start": today.isoformat(), "period_end": (today + timedelta(days=20)).isoformat(), "allocated_amount": "250.00",
    })
    assert budget.status_code == 201, budget.text
    request_id = _make_submitted_request(finance_world, budget_id=budget.json()["id"])
    approved = approver.post(f"/api/v1/finance/payment-requests/{request_id}/approve", headers=_headers(approver), json={"note": "Budget checked"})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"
    first = approver.post(f"/api/v1/finance/payment-requests/{request_id}/execute", headers=_headers(approver))
    replay = approver.post(f"/api/v1/finance/payment-requests/{request_id}/execute", headers=_headers(approver))
    assert first.status_code == replay.status_code == 200, first.text
    assert first.json()["payment_id"] == replay.json()["payment_id"]
    assert replay.json()["status"] == "COMPLETED"
    budgets = approver.get("/api/v1/finance/budgets").json()["items"]
    assert budgets[0]["spent_amount"] == "100.00"
    assert budgets[0]["committed_amount"] == "0.00"
    assert budgets[0]["remaining_amount"] == "150.00"
    history = approver.get(f"/api/v1/finance/payment-requests/{request_id}/history")
    assert [event["to_status"] for event in history.json()["items"]] == ["DRAFT", "SUBMITTED", "APPROVED", "PAYMENT_CREATED", "COMPLETED"]
    assert [event["sequence_number"] for event in history.json()["items"]] == [1, 2, 3, 4, 5]
    finance_activity = approver.get("/api/v1/activity?type=finance").json()["items"]
    request_activity = [item for item in finance_activity if item["finance_record_type"] == "payment_request" and item["payment_request_id"] == request_id]
    assert [item["event_status"] for item in reversed(request_activity)] == ["DRAFT", "SUBMITTED", "APPROVED", "PAYMENT_CREATED", "COMPLETED"]
    assert request_activity[0]["payment_id"] == replay.json()["payment_id"]
    budget_activity = [item for item in finance_activity if item["finance_record_type"] == "budget"]
    assert len(budget_activity) == 1
    assert budget_activity[0]["budget_id"] == budget.json()["id"]
    assert budget_activity[0]["title"] == "Budget created"
    requester_activity = requester.get("/api/v1/activity?type=finance").json()["items"]
    assert any(item.get("payment_request_id") == request_id for item in requester_activity)
    with database.session_factory() as session:
        payment = session.get(Payment, UUID(replay.json()["payment_id"]))
        assert payment is not None
        ledger = session.scalar(select(LedgerTransaction).where(LedgerTransaction.payment_id == payment.id))
        assert ledger is not None
        entries = session.scalars(select(LedgerEntry).where(LedgerEntry.ledger_transaction_id == ledger.id)).all()
        assert payment.sender_organization_id == UUID(str(finance_world["organization_id"]))
        assert len(entries) == 2


def test_budget_reserves_approved_requests_and_rejects_overcommit(finance_world: dict[str, object]) -> None:
    approver = finance_world["approver"]
    assert isinstance(approver, TestClient)
    today = date.today()
    budget = approver.post("/api/v1/finance/budgets", headers=_headers(approver), json={
        "organization_id": finance_world["organization_id"], "name": "Office", "period_start": today.isoformat(),
        "period_end": (today + timedelta(days=2)).isoformat(), "allocated_amount": "100.00",
    })
    assert budget.status_code == 201
    ids = [_make_submitted_request(finance_world, amount="75.00", key=f"request-key-{index}", budget_id=budget.json()["id"]) for index in range(2)]
    first = approver.post(f"/api/v1/finance/payment-requests/{ids[0]}/approve", headers=_headers(approver), json={})
    second = approver.post(f"/api/v1/finance/payment-requests/{ids[1]}/approve", headers=_headers(approver), json={})
    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "BUDGET_EXCEEDED"


def test_request_separation_of_duties_and_organization_scoping(finance_world: dict[str, object]) -> None:
    requester = finance_world["requester"]
    recipient = finance_world["recipient"]
    assert isinstance(requester, TestClient) and isinstance(recipient, TestClient)
    request_id = _make_submitted_request(finance_world)
    self_approval = requester.post(f"/api/v1/finance/payment-requests/{request_id}/approve", headers=_headers(requester), json={})
    outsider_read = recipient.get("/api/v1/finance/payment-requests").json()["items"]
    outsider_detail = recipient.get(f"/api/v1/finance/payment-requests/{request_id}/history")
    assert self_approval.status_code == 403
    assert outsider_read == []
    assert outsider_detail.status_code == 404


def test_rejection_reason_transition_validation_idempotency_and_csrf(finance_world: dict[str, object]) -> None:
    requester = finance_world["requester"]
    approver = finance_world["approver"]
    assert isinstance(requester, TestClient) and isinstance(approver, TestClient)
    first = _create_request(finance_world, key="same-request-key")
    replay = _create_request(finance_world, key="same-request-key")
    conflict = _create_request(finance_world, key="same-request-key", amount="101.00")
    assert first.status_code == replay.status_code == 201
    assert first.json()["id"] == replay.json()["id"]
    assert conflict.status_code == 409
    no_csrf = requester.post("/api/v1/finance/payment-requests", json={
        "organization_id": finance_world["organization_id"], "recipient_account": finance_world["recipient_account"],
        "amount": "10.00", "purpose": "invoice",
    }, headers={"Idempotency-Key": "without-csrf"})
    request_id = _make_submitted_request(finance_world, key="reject-request-key")
    rejected = approver.post(f"/api/v1/finance/payment-requests/{request_id}/reject", headers=_headers(approver), json={})
    assert no_csrf.status_code == 403
    assert rejected.status_code == 422


def test_finance_is_non_cacheable_and_amount_validation_is_strict(finance_world: dict[str, object]) -> None:
    requester = finance_world["requester"]
    assert isinstance(requester, TestClient)
    response = requester.get("/api/v1/finance/budgets")
    bad = requester.post("/api/v1/finance/payment-requests", headers=_headers(requester), json={
        "organization_id": finance_world["organization_id"], "recipient_account": finance_world["recipient_account"],
        "amount": 1.25, "purpose": "invoice",
    })
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert bad.status_code == 422


