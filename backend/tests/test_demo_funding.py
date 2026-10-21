
import pytest

pytestmark = pytest.mark.skip(
    reason='Demo-funding write workflow is intentionally excluded from this public source distribution.',
)

from collections.abc import Iterator
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
from app.models.demo_funding import DemoFunding

PASSWORD = "LedgerChain1!"


@pytest.fixture
def demo_funding_world() -> Iterator[dict[str, object]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    database = Database(engine=engine, session_factory=create_session_factory(engine))
    app = create_app(Settings(_env_file=None, environment="test", cors_origins="http://localhost:3000"), database)
    with TestClient(app, raise_server_exceptions=False) as client:
        registered = client.post("/api/v1/auth/register", json={"email": "funding@example.com", "password": PASSWORD})
        assert registered.status_code == 201, registered.text
        logged_in = client.post("/api/v1/auth/login", json={"email": "funding@example.com", "password": PASSWORD})
        assert logged_in.status_code == 200, logged_in.text
        account_response = client.get("/api/v1/account")
        assert account_response.status_code == 200, account_response.text
        account = account_response.json()
        user_id = UUID(logged_in.json()["user"]["id"])
        yield {
            "database": database,
            "client": client,
            "account": account,
            "user_id": user_id,
            "organization_id": UUID(account["id"]),
        }
    database.dispose()


def _headers(client: TestClient, key: str = "demo-funding-test-001") -> dict[str, str]:
    csrf_token = client.cookies.get("ledgerchain_csrf")
    assert csrf_token
    return {"X-CSRF-Token": csrf_token, "Idempotency-Key": key}


def _fund(world: dict[str, object], amount: str = "1250.50", key: str = "demo-funding-test-001"):
    client = world["client"]
    assert isinstance(client, TestClient)
    return client.post("/api/v1/demo-fundings/demo", headers=_headers(client, key), json={"amount": amount})


def test_demo_funding_updates_account_and_records_a_demo_receipt(demo_funding_world: dict[str, object]) -> None:
    response = _fund(demo_funding_world)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["amount"] == "1250.50"
    assert body["balance"] == "1250.50"
    assert body["currency"] == "INR"
    assert body["demo"] is True
    assert body["reference"].startswith("LC-DEMO-FUND-")

    database = demo_funding_world["database"]
    organization_id = demo_funding_world["organization_id"]
    assert isinstance(database, Database) and isinstance(organization_id, UUID)
    with database.session_factory() as session:
        organization = session.get(Organization, organization_id)
        funding = session.scalar(select(DemoFunding).where(DemoFunding.reference == body["reference"]))
        assert organization is not None and organization.balance == Decimal("1250.50")
        assert funding is not None and funding.user_id == demo_funding_world["user_id"]


def test_demo_funding_replay_does_not_credit_twice(demo_funding_world: dict[str, object]) -> None:
    first = _fund(demo_funding_world, key="funding-retry-key-01")
    replay = _fund(demo_funding_world, key="funding-retry-key-01")
    assert first.status_code == replay.status_code == 201
    assert first.json()["id"] == replay.json()["id"]
    assert replay.json()["balance"] == "1250.50"

    database = demo_funding_world["database"]
    organization_id = demo_funding_world["organization_id"]
    assert isinstance(database, Database) and isinstance(organization_id, UUID)
    with database.session_factory() as session:
        organization = session.get(Organization, organization_id)
        assert organization is not None and organization.balance == Decimal("1250.50")
        assert len(session.scalars(select(DemoFunding)).all()) == 1


def test_demo_funding_rejects_reused_key_with_different_amount(demo_funding_world: dict[str, object]) -> None:
    _fund(demo_funding_world, key="funding-conflict-key-01")
    response = _fund(demo_funding_world, amount="1251.00", key="funding-conflict-key-01")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


@pytest.mark.parametrize("amount", ["0", "-1", "1.001", "NaN", "1000000.01", 10.25])
def test_demo_funding_rejects_invalid_amounts_without_changing_balance(
    demo_funding_world: dict[str, object], amount: object
) -> None:
    client = demo_funding_world["client"]
    assert isinstance(client, TestClient)
    response = client.post(
        "/api/v1/demo-fundings/demo",
        headers=_headers(client, f"invalid-funding-{str(amount)}"),
        json={"amount": amount},
    )
    assert response.status_code == 422
    assert client.get("/api/v1/account").json()["balance"] == "0.00"


def test_demo_funding_requires_existing_session(demo_funding_world: dict[str, object]) -> None:
    client = demo_funding_world["client"]
    assert isinstance(client, TestClient)
    client.cookies.clear()
    response = client.post("/api/v1/demo-fundings/demo", json={"amount": "100.00"})
    assert response.status_code == 401

