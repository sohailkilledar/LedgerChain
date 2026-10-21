from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from app.api.dependencies.auth import authorize_resource_owner
from app.core.config import Settings
from app.core.errors import AuthorizationError
from app.db.base import Base
from app.db.session import Database, create_session_factory
from app.main import create_app
from app.models.account import Organization
from app.models.auth import AuthSession, AuthToken, User
from app.services.auth import hash_token

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
    with TestClient(auth_app, raise_server_exceptions=False) as client:
        yield client


def register_user(client: TestClient, email: str = "person@example.com") -> None:
    response = client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text


def issue_email_verification_token(auth_database: Database, email: str) -> str:
    raw_token = f"email-verification-test-{uuid4().hex}"
    with auth_database.session_factory() as session:
        user = session.scalar(select(User).where(User.email == email))
        assert user is not None
        user.email_verified = False
        session.add(
            AuthToken(
                user_id=user.id,
                purpose="email_verification",
                token_hash=hash_token(raw_token),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        session.commit()
    return raw_token


def login(client: TestClient, email: str = "person@example.com", password: str = PASSWORD) -> TestClient:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return client


def test_register_creates_hashed_user_without_verification_token(
    auth_client: TestClient, auth_database: Database
) -> None:
    response = auth_client.post("/api/v1/auth/register", json={"email": " Person@Example.com ", "password": PASSWORD})

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "person@example.com"
    assert body["user"]["email_verified"] is True
    assert "password" not in str(body).lower()
    assert PASSWORD not in response.text
    assert "development_token" not in body
    with auth_database.session_factory() as session:
        user = session.scalar(select(User).where(User.email == "person@example.com"))
        assert user is not None
        assert user.password_hash != PASSWORD
        assert user.password_hash.startswith("$argon2id$")
        assert session.scalar(select(AuthToken).where(AuthToken.user_id == user.id)) is None


def test_register_persists_profile_and_organization_names(auth_client: TestClient, auth_database: Database) -> None:
    response = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "founder@example.com",
            "password": PASSWORD,
            "display_name": "  Ada Founder  ",
            "organization_name": "  Acme Ledger  ",
        },
    )

    assert response.status_code == 201
    with auth_database.session_factory() as session:
        user = session.scalar(select(User).where(User.email == "founder@example.com"))
        organization = session.scalar(select(Organization).where(Organization.name == "Acme Ledger"))
        assert user is not None and user.display_name == "Ada Founder"
        assert organization is not None


def test_register_rejects_invalid_email_and_password_with_standard_errors(auth_client: TestClient) -> None:
    invalid_email = auth_client.post("/api/v1/auth/register", json={"email": "not-an-email", "password": PASSWORD})
    invalid_password = auth_client.post(
        "/api/v1/auth/register", json={"email": "person@example.com", "password": "short"}
    )

    assert invalid_email.status_code == invalid_password.status_code == 422
    assert invalid_email.json()["error"]["code"] == "VALIDATION_ERROR"
    assert invalid_password.json()["error"]["code"] == "INVALID_PASSWORD"
    for response in (invalid_email, invalid_password):
        assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_register_duplicate_email_is_case_insensitive(auth_client: TestClient) -> None:
    register_user(auth_client)
    response = auth_client.post("/api/v1/auth/register", json={"email": "PERSON@example.com", "password": PASSWORD})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_login_uses_email_and_password_without_verification(auth_client: TestClient, auth_database: Database) -> None:
    register_user(auth_client)
    with auth_database.session_factory() as session:
        user = session.scalar(select(User).where(User.email == "person@example.com"))
        assert user is not None
        user.email_verified = False
        session.commit()

    response = auth_client.post("/api/v1/auth/login", json={"email": "person@example.com", "password": PASSWORD})

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "person@example.com"
    assert auth_client.get("/api/v1/auth/me").status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert "password_hash" not in response.text
    assert PASSWORD not in response.text
    assert auth_client.cookies.get("ledgerchain_session")
    assert auth_client.cookies.get("ledgerchain_csrf")
    assert "ledgerchain_session" in response.headers["set-cookie"]
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "ledgerchain_csrf" in response.headers["set-cookie"]
    session_token = auth_client.cookies.get("ledgerchain_session")
    with auth_database.session_factory() as session:
        stored_session = session.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(session_token)))
        assert stored_session is not None
        assert stored_session.token_hash != session_token
        assert stored_session.csrf_token_hash == hash_token(auth_client.cookies.get("ledgerchain_csrf"))


def test_invalid_password_and_unknown_email_share_safe_auth_error(auth_client: TestClient) -> None:
    register_user(auth_client)
    wrong_password = auth_client.post("/api/v1/auth/login", json={"email": "person@example.com", "password": "Wrong1!Pass"})
    missing_user = auth_client.post("/api/v1/auth/login", json={"email": "missing@example.com", "password": "Wrong1!Pass"})

    assert wrong_password.status_code == missing_user.status_code == 401
    assert wrong_password.json()["error"]["code"] == missing_user.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert wrong_password.json()["error"]["message"] == missing_user.json()["error"]["message"]


def test_inactive_account_cannot_log_in(auth_client: TestClient, auth_database: Database) -> None:
    register_user(auth_client)
    with auth_database.session_factory() as session:
        user = session.scalar(select(User).where(User.email == "person@example.com"))
        assert user is not None
        user.account_status = "suspended"
        session.commit()

    response = auth_client.post("/api/v1/auth/login", json={"email": "person@example.com", "password": PASSWORD})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_me_requires_valid_session_and_logout_revokes_it(auth_client: TestClient) -> None:
    unauthenticated = auth_client.get("/api/v1/auth/me")
    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    register_user(auth_client)
    login(auth_client)
    response = auth_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "person@example.com"
    assert "password_hash" not in response.text

    csrf_token = auth_client.cookies.get("ledgerchain_csrf")
    logout = auth_client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout.status_code == 204
    assert auth_client.get("/api/v1/auth/me").status_code == 401


def test_logout_requires_csrf_for_authenticated_session(auth_client: TestClient) -> None:
    register_user(auth_client)
    login(auth_client)
    response = auth_client.post("/api/v1/auth/logout")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_VALIDATION_FAILED"
    assert auth_client.get("/api/v1/auth/me").status_code == 200


def test_expired_session_is_rejected(auth_client: TestClient, auth_database: Database) -> None:
    register_user(auth_client)
    login(auth_client)
    raw_token = auth_client.cookies.get("ledgerchain_session")
    with auth_database.session_factory() as session:
        auth_session = session.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(raw_token)))
        assert auth_session is not None
        auth_session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()

    assert auth_client.get("/api/v1/auth/me").status_code == 401


@pytest.mark.parametrize("token_kind", ["invalid", "expired", "reused"])
def test_email_verification_rejects_invalid_expired_or_reused_tokens(
    auth_client: TestClient, auth_database: Database, token_kind: str
) -> None:
    register_user(auth_client)
    token = issue_email_verification_token(auth_database, "person@example.com")
    if token_kind == "invalid":
        token = "x" * 48
    elif token_kind == "expired":
        with auth_database.session_factory() as session:
            record = session.scalar(select(AuthToken).where(AuthToken.token_hash == hash_token(token)))
            assert record is not None
            record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            session.commit()
    elif token_kind == "reused":
        assert auth_client.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 200

    response = auth_client.post("/api/v1/auth/verify-email", json={"token": token})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_OR_EXPIRED_TOKEN"


def test_email_verification_success_sets_verified_state(auth_client: TestClient, auth_database: Database) -> None:
    register_user(auth_client)
    token = issue_email_verification_token(auth_database, "person@example.com")
    verified = auth_client.post("/api/v1/auth/verify-email", json={"token": token})

    assert verified.status_code == 200
    assert verified.json()["user"]["email_verified"] is True
    assert "password_hash" not in verified.text
    assert auth_client.post("/api/v1/auth/login", json={"email": "person@example.com", "password": PASSWORD}).status_code == 200


def test_forgot_password_response_does_not_reveal_account_existence(
    auth_client: TestClient, auth_database: Database
) -> None:
    register_user(auth_client)
    known = auth_client.post("/api/v1/auth/forgot-password", json={"email": "person@example.com"})
    unknown = auth_client.post("/api/v1/auth/forgot-password", json={"email": "missing@example.com"})

    assert known.status_code == unknown.status_code == 200
    assert known.json()["message"] == unknown.json()["message"]
    assert set(known.json()) == set(unknown.json())
    assert known.json()["development_token"] != unknown.json()["development_token"]
    with auth_database.session_factory() as session:
        reset_record = session.scalar(
            select(AuthToken).where(AuthToken.token_hash == hash_token(known.json()["development_token"]))
        )
        assert reset_record is not None
        assert reset_record.token_hash != known.json()["development_token"]


def test_password_reset_changes_password_and_revokes_sessions(auth_client: TestClient, auth_database: Database) -> None:
    register_user(auth_client)
    login(auth_client)
    old_session_token = auth_client.cookies.get("ledgerchain_session")
    token_response = auth_client.post("/api/v1/auth/forgot-password", json={"email": "person@example.com"})
    token = token_response.json()["development_token"]
    reset = auth_client.post(
        "/api/v1/auth/reset-password", json={"token": token, "password": "Replacement2!"}
    )

    assert reset.status_code == 200
    assert auth_client.get("/api/v1/auth/me").status_code == 401
    assert auth_client.post("/api/v1/auth/login", json={"email": "person@example.com", "password": PASSWORD}).status_code == 401
    assert auth_client.post(
        "/api/v1/auth/login", json={"email": "person@example.com", "password": "Replacement2!"}
    ).status_code == 200
    with auth_database.session_factory() as session:
        old_session = session.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(old_session_token)))
        assert old_session is not None
        assert old_session.revoked_at is not None


def test_password_reset_rejects_invalid_expired_and_reused_tokens(
    auth_client: TestClient, auth_database: Database
) -> None:
    register_user(auth_client)
    issued = auth_client.post("/api/v1/auth/forgot-password", json={"email": "person@example.com"})
    expired_token = issued.json()["development_token"]
    with auth_database.session_factory() as session:
        record = session.scalar(select(AuthToken).where(AuthToken.token_hash == hash_token(expired_token)))
        assert record is not None
        record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()

    for invalid_token in ("x" * 48, expired_token):
        response = auth_client.post(
            "/api/v1/auth/reset-password", json={"token": invalid_token, "password": "Replacement2!"}
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_OR_EXPIRED_TOKEN"

    fresh = auth_client.post("/api/v1/auth/forgot-password", json={"email": "person@example.com"})
    token = fresh.json()["development_token"]
    assert auth_client.post(
        "/api/v1/auth/reset-password", json={"token": token, "password": "Replacement2!"}
    ).status_code == 200
    reused = auth_client.post("/api/v1/auth/reset-password", json={"token": token, "password": "Replacement3!"})
    assert reused.status_code == 422
    assert reused.json()["error"]["code"] == "INVALID_OR_EXPIRED_TOKEN"


def test_production_responses_never_include_development_tokens(auth_database: Database) -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        secret_key="production-test-secret-not-used-for-auth",
        database_url="postgresql+psycopg://ledgerchain:local@localhost/ledgerchain",
        blockchain_enabled=False,
    )
    app = create_app(settings, auth_database)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/v1/auth/register", json={"email": "person@example.com", "password": PASSWORD})

    assert response.status_code == 201
    assert "development_token" not in response.json()


def test_auth_post_rejects_unconfigured_browser_origin(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "person@example.com", "password": PASSWORD},
        headers={"Origin": "https://untrusted.example"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORIGIN_NOT_ALLOWED"


def test_auth_rate_limiter_returns_standardized_429(auth_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.auth.PasswordService.verify", lambda *_args: False)
    for _ in range(10):
        auth_client.post("/api/v1/auth/login", json={"email": "missing@example.com", "password": PASSWORD})
    response = auth_client.post("/api/v1/auth/login", json={"email": "missing@example.com", "password": PASSWORD})

    assert response.status_code == 429
    assert response.headers["Retry-After"]
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_openapi_documents_versioned_authentication_endpoints(auth_client: TestClient) -> None:
    schema = auth_client.get("/openapi.json").json()

    assert "/api/v1/auth/register" in schema["paths"]
    assert "/api/v1/auth/login" in schema["paths"]
    assert "/api/v1/auth/logout" in schema["paths"]
    assert "/api/v1/auth/me" in schema["paths"]
    assert "/api/v1/auth/verify-email" in schema["paths"]
    assert "/api/v1/auth/forgot-password" in schema["paths"]
    assert "/api/v1/auth/reset-password" in schema["paths"]


def test_auth_responses_keep_standard_error_envelope(auth_client: TestClient) -> None:
    response = auth_client.post("/api/v1/auth/login", json={"email": "person@example.com", "password": PASSWORD})

    assert response.status_code == 401
    assert set(response.json()) == {"error"}
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
    assert PASSWORD not in response.text
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_credentials_and_action_tokens_are_not_written_to_logs(auth_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    register_user(auth_client)
    auth_client.post("/api/v1/auth/login", json={"email": "person@example.com", "password": PASSWORD})
    reset_response = auth_client.post("/api/v1/auth/forgot-password", json={"email": "person@example.com"})
    reset_token = reset_response.json()["development_token"]

    assert PASSWORD not in caplog.text
    assert reset_token not in caplog.text


def test_unhandled_error_does_not_log_exception_secret(auth_app: FastAPI, caplog: pytest.LogCaptureFixture) -> None:
    secret = "exception-secret-token"

    def raise_secret_error() -> None:
        raise RuntimeError(secret)

    auth_app.add_api_route("/_test/auth-secret-error", raise_secret_error)
    with TestClient(auth_app, raise_server_exceptions=False) as client:
        response = client.get("/_test/auth-secret-error")

    assert response.status_code == 500
    assert secret not in caplog.text



def test_resource_owner_policy_rejects_another_users_resource() -> None:
    owner = User(id=uuid4(), email="owner@example.com", password_hash="not-used")
    other_owner_id = uuid4()

    with pytest.raises(AuthorizationError) as exc_info:
        authorize_resource_owner(owner, other_owner_id)
    assert exc_info.value.code == "RESOURCE_ACCESS_DENIED"
