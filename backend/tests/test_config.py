import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_cors_origins_are_parsed_from_comma_separated_string() -> None:
    settings = Settings(_env_file=None, cors_origins="http://localhost:3000, https://app.example.com")

    assert settings.cors_origin_list == ["http://localhost:3000", "https://app.example.com"]


def test_production_rejects_default_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production")


def test_production_accepts_real_secrets() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        secret_key="a-real-secret-value",
        database_url="postgresql+psycopg://user:real-password@db/ledgerchain",
        blockchain_enabled=False,
    )

    assert settings.is_production


def test_production_disables_unverified_development_provider() -> None:
    with pytest.raises(ValidationError, match="BLOCKCHAIN_ENABLED"):
        Settings(
            _env_file=None,
            environment="production",
            secret_key="a-real-secret-value",
            database_url="postgresql+psycopg://user:real-password@db/ledgerchain",
            blockchain_enabled=True,
        )


def test_secret_is_not_exposed_in_repr() -> None:
    settings = Settings(_env_file=None, secret_key="super-secret")

    assert "super-secret" not in repr(settings)
