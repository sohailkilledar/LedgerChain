import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    InternalError,
    NotFoundError,
    ValidationError,
)


class _Payload(BaseModel):
    amount: int


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    @app.get("/_test/app-error/{kind}")
    def raise_app_error(kind: str) -> None:
        errors: dict[str, AppError] = {
            "validation": ValidationError(),
            "authentication": AuthenticationError(),
            "authorization": AuthorizationError(),
            "not_found": NotFoundError(),
            "conflict": ConflictError(code="EMAIL_IN_USE", message="Email already registered."),
            "internal": InternalError(committed=True),
        }
        raise errors[kind]

    @app.get("/_test/crash")
    def crash() -> None:
        raise RuntimeError("database password is hunter2")

    @app.post("/_test/validate")
    def validate(payload: _Payload) -> _Payload:
        return payload

    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("kind", "status", "code", "retryable"),
    [
        ("validation", 422, "VALIDATION_ERROR", False),
        ("authentication", 401, "AUTHENTICATION_REQUIRED", False),
        ("authorization", 403, "FORBIDDEN", False),
        ("not_found", 404, "NOT_FOUND", False),
        ("conflict", 409, "EMAIL_IN_USE", False),
        ("internal", 500, "INTERNAL_ERROR", True),
    ],
)
def test_app_errors_use_consistent_shape(
    client: TestClient, kind: str, status: int, code: str, retryable: bool
) -> None:
    response = client.get(f"/_test/app-error/{kind}")

    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    assert error["retryable"] is retryable
    assert isinstance(error["message"], str) and error["message"]
    assert error["request_id"] == response.headers["X-Request-ID"]


def test_custom_message_and_committed_flag(client: TestClient) -> None:
    assert client.get("/_test/app-error/conflict").json()["error"]["message"] == "Email already registered."
    assert client.get("/_test/app-error/internal").json()["error"]["committed"] is True


def test_unhandled_exception_hides_internal_details(client: TestClient) -> None:
    response = client.get("/_test/crash")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "hunter2" not in response.text


def test_request_validation_returns_field_errors(client: TestClient) -> None:
    response = client.post("/_test/validate", json={"amount": "not-a-number"})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["fields"][0]["field"] == "body.amount"


def test_unknown_route_returns_not_found_shape(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
