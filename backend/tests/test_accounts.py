from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base
from app.db.session import Database, create_session_factory
from app.main import create_app
from app.models.account import (
    NotificationPreferences,
    Organization,
    OrganizationMembership,
    UserSettings,
)
PASSWORD = "LedgerChain1!"


@pytest.fixture
def auth_database() -> Iterator[Database]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield Database(engine=engine, session_factory=create_session_factory(engine))
    engine.dispose()


@pytest.fixture
def auth_app(auth_database: Database) -> FastAPI:
    return create_app(Settings(_env_file=None, environment="test", cors_origins="http://localhost:3000"), auth_database)


@pytest.fixture
def auth_client(auth_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(auth_app, raise_server_exceptions=False) as test_client:
        yield test_client


def create_signed_in_user(client: TestClient, email: str) -> UUID:
    registered = client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})
    assert registered.status_code == 201, registered.text
    signed_in = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert signed_in.status_code == 200, signed_in.text
    return UUID(signed_in.json()["user"]["id"])


def csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("ledgerchain_csrf")
    assert token
    return {"X-CSRF-Token": token}


def test_profile_is_authenticated_safe_and_read_only_email(auth_client: TestClient) -> None:
    anonymous = auth_client.get("/api/v1/users/me")
    assert anonymous.status_code == 401

    create_signed_in_user(auth_client, "profile@example.com")
    profile = auth_client.get("/api/v1/users/me")
    assert profile.status_code == 200
    assert profile.json()["email"] == "profile@example.com"
    assert profile.json()["email_verified"] is True
    assert "password_hash" not in profile.text
    assert "session" not in profile.text.lower()
    assert profile.headers["cache-control"] == "no-store"

    updated = auth_client.patch(
        "/api/v1/users/me",
        headers=csrf_headers(auth_client),
        json={"display_name": "  Meera Kulkarni  ", "phone": "+91 98200 41177"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["display_name"] == "Meera Kulkarni"
    assert updated.json()["phone"] == "+91 98200 41177"

    email_change = auth_client.patch(
        "/api/v1/users/me", headers=csrf_headers(auth_client), json={"email": "other@example.com"}
    )
    password_change = auth_client.patch(
        "/api/v1/users/me", headers=csrf_headers(auth_client), json={"password_hash": "attacker"}
    )
    blank_name = auth_client.patch(
        "/api/v1/users/me", headers=csrf_headers(auth_client), json={"display_name": "   "}
    )
    assert email_change.status_code == password_change.status_code == blank_name.status_code == 422


def test_registration_creates_owner_membership_and_persistent_defaults(
    auth_client: TestClient, auth_database: Database
) -> None:
    user_id = create_signed_in_user(auth_client, "owner@example.com")
    with auth_database.session_factory() as session:
        membership = session.scalar(
            select(OrganizationMembership).where(OrganizationMembership.user_id == user_id)
        )
        organization = session.get(Organization, membership.organization_id) if membership else None
        assert membership is not None and membership.role == "owner"
        assert organization is not None and organization.name == "My organization"
        assert session.scalar(select(UserSettings).where(UserSettings.user_id == user_id)) is not None
        assert session.scalar(
            select(NotificationPreferences).where(NotificationPreferences.user_id == user_id)
        ) is not None


def test_organization_owner_can_read_and_update_allowed_fields(auth_client: TestClient) -> None:
    create_signed_in_user(auth_client, "organization-owner@example.com")
    before = auth_client.get("/api/v1/account")
    assert before.status_code == 200
    assert before.json()["role"] == "owner"

    changed = auth_client.patch(
        "/api/v1/account",
        headers=csrf_headers(auth_client),
        json={"name": "Kulkarni Exports", "account_type": "partnership"},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["name"] == "Kulkarni Exports"
    assert changed.json()["account_type"] == "partnership"

    invalid_type = auth_client.patch(
        "/api/v1/account", headers=csrf_headers(auth_client), json={"account_type": "wallet"}
    )
    blank_name = auth_client.patch("/api/v1/account", headers=csrf_headers(auth_client), json={"name": "  "})
    assert invalid_type.status_code == blank_name.status_code == 422


def test_member_can_read_but_cannot_update_organization(
    auth_client: TestClient, auth_database: Database
) -> None:
    user_id = create_signed_in_user(auth_client, "member@example.com")
    with auth_database.session_factory() as session:
        membership = session.scalar(
            select(OrganizationMembership).where(OrganizationMembership.user_id == user_id)
        )
        assert membership is not None
        membership.role = "member"
        session.commit()

    assert auth_client.get("/api/v1/account").status_code == 200
    forbidden = auth_client.patch(
        "/api/v1/account", headers=csrf_headers(auth_client), json={"name": "Not allowed"}
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "OWNER_REQUIRED"


def test_user_without_membership_cannot_access_account(
    auth_client: TestClient, auth_database: Database
) -> None:
    user_id = create_signed_in_user(auth_client, "no-membership@example.com")
    with auth_database.session_factory() as session:
        session.execute(delete(OrganizationMembership).where(OrganizationMembership.user_id == user_id))
        session.commit()

    response = auth_client.get("/api/v1/account")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


def test_settings_are_validated_and_scoped_to_the_signed_in_user(
    auth_client: TestClient, auth_app, auth_database: Database
) -> None:
    first_user_id = create_signed_in_user(auth_client, "settings-one@example.com")
    initial = auth_client.get("/api/v1/users/me/settings")
    assert initial.status_code == 200
    assert initial.json()["time_zone"] == "UTC"

    saved = auth_client.patch(
        "/api/v1/users/me/settings",
        headers=csrf_headers(auth_client),
        json={"time_zone": "Asia/Kolkata", "date_format": "iso", "share_usage_data": True},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["time_zone"] == "Asia/Kolkata"
    assert saved.json()["date_format"] == "iso"
    assert saved.json()["share_usage_data"] is True

    invalid_zone = auth_client.patch(
        "/api/v1/users/me/settings", headers=csrf_headers(auth_client), json={"time_zone": "Not/AZone"}
    )
    invalid_locale = auth_client.patch(
        "/api/v1/users/me/settings", headers=csrf_headers(auth_client), json={"locale": "English"}
    )
    invalid_format = auth_client.patch(
        "/api/v1/users/me/settings", headers=csrf_headers(auth_client), json={"date_format": "year-month-day"}
    )
    null_boolean = auth_client.patch(
        "/api/v1/users/me/settings", headers=csrf_headers(auth_client), json={"share_usage_data": None}
    )
    assert invalid_zone.status_code == invalid_locale.status_code == invalid_format.status_code == null_boolean.status_code == 422

    with TestClient(auth_app, raise_server_exceptions=False) as other_client:
        second_user_id = create_signed_in_user(other_client, "settings-two@example.com")
        assert second_user_id != first_user_id
        cross_user_update = other_client.patch(
            "/api/v1/users/me/settings",
            headers=csrf_headers(other_client),
            json={"user_id": str(first_user_id), "time_zone": "Europe/London"},
        )
        assert cross_user_update.status_code == 422
        other = other_client.patch(
            "/api/v1/users/me/settings",
            headers=csrf_headers(other_client),
            json={"time_zone": "Europe/London"},
        )
        assert other.status_code == 200
        with auth_database.session_factory() as session:
            first_settings = session.scalar(select(UserSettings).where(UserSettings.user_id == first_user_id))
            assert first_settings is not None and first_settings.time_zone == "Asia/Kolkata"


def test_notification_preferences_can_be_read_and_updated(auth_client: TestClient) -> None:
    create_signed_in_user(auth_client, "notifications@example.com")
    initial = auth_client.get("/api/v1/users/me/notifications")
    assert initial.status_code == 200
    assert initial.json()["security_notifications"] is True

    updated = auth_client.patch(
        "/api/v1/users/me/notifications",
        headers=csrf_headers(auth_client),
        json={"security_notifications": False, "transaction_notifications": False, "marketing_notifications": True},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["security_notifications"] is False
    assert updated.json()["transaction_notifications"] is False
    assert updated.json()["marketing_notifications"] is True

    invalid = auth_client.patch(
        "/api/v1/users/me/notifications",
        headers=csrf_headers(auth_client),
        json={"account_notifications": "sometimes"},
    )
    null_value = auth_client.patch(
        "/api/v1/users/me/notifications", headers=csrf_headers(auth_client), json={"account_notifications": None}
    )
    assert invalid.status_code == null_value.status_code == 422
