from functools import lru_cache
import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "change-me"
# Matches the credentials of the local docker-compose `db` service. Never valid in production.
DEFAULT_DATABASE_URL = "postgresql+psycopg://ledgerchain:ledgerchain@localhost:5432/ledgerchain"

_PSYCOPG_DRIVER = "postgresql+psycopg://"
_BARE_POSTGRES_SCHEMES = ("postgresql://", "postgres://")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LEDGERCHAIN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "LedgerChain API"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"

    database_url: SecretStr = SecretStr(DEFAULT_DATABASE_URL)
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=10, ge=0)
    database_pool_timeout: float = Field(default=30.0, gt=0)
    database_pool_recycle: int = Field(default=1800, ge=-1)
    database_connect_timeout: int = Field(default=5, ge=1)
    database_echo: bool = False

    secret_key: SecretStr = SecretStr(DEFAULT_SECRET_KEY)

    blockchain_enabled: bool = True
    blockchain_provider: str = Field(default="development", min_length=1, max_length=32)
    blockchain_network: str = Field(default="local-simulation", min_length=1, max_length=64)
    blockchain_chain_id: int | None = Field(default=None, gt=0)
    blockchain_rpc_url: SecretStr | None = None
    blockchain_signer_private_key: SecretStr | None = None
    blockchain_contract_address: str | None = Field(default=None, min_length=42, max_length=42)
    blockchain_contract_version: str = Field(default="1.0.0", min_length=1, max_length=24)
    blockchain_rpc_timeout_seconds: int = Field(default=10, ge=1, le=60)
    blockchain_confirmation_depth: int = Field(default=1, ge=1, le=128)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        """Database URL with the psycopg 3 driver made explicit.

        Hosting providers usually hand out bare ``postgresql://`` / ``postgres://`` URLs,
        which SQLAlchemy would otherwise map to psycopg2.
        """
        url = self.database_url.get_secret_value()
        for scheme in _BARE_POSTGRES_SCHEMES:
            if url.startswith(scheme):
                return _PSYCOPG_DRIVER + url[len(scheme) :]
        return url

    @model_validator(mode="after")
    def _require_real_secrets_in_production(self) -> "Settings":
        if self.blockchain_enabled and self.blockchain_provider == "evm":
            self._validate_evm_configuration()
        if not self.is_production:
            return self
        if self.secret_key.get_secret_value() == DEFAULT_SECRET_KEY:
            raise ValueError("LEDGERCHAIN_SECRET_KEY must be set to a real secret in production")
        if self.sqlalchemy_database_url == DEFAULT_DATABASE_URL:
            raise ValueError("LEDGERCHAIN_DATABASE_URL must be set to real credentials in production")
        if self.blockchain_enabled and self.blockchain_provider != "evm":
            raise ValueError(
                "LEDGERCHAIN_BLOCKCHAIN_ENABLED in production requires a configured real EVM provider"
            )
        return self

    def _validate_evm_configuration(self) -> None:
        if self.blockchain_chain_id is None:
            raise ValueError("LEDGERCHAIN_BLOCKCHAIN_CHAIN_ID is required for the EVM provider")
        if self.blockchain_rpc_url is None or self.blockchain_signer_private_key is None:
            raise ValueError("The EVM provider requires an RPC URL and backend signer key")
        if self.blockchain_contract_address is None or not re.fullmatch(
            r"0x[0-9a-fA-F]{40}", self.blockchain_contract_address
        ):
            raise ValueError("LEDGERCHAIN_BLOCKCHAIN_CONTRACT_ADDRESS must be a 20-byte EVM address")
        rpc = self.blockchain_rpc_url.get_secret_value()
        parsed = urlsplit(rpc)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("LEDGERCHAIN_BLOCKCHAIN_RPC_URL must be an HTTP(S) endpoint")
        if self.is_production and parsed.scheme != "https":
            raise ValueError("The EVM RPC endpoint must use HTTPS in production")
        if not re.fullmatch(r"(?:0x)?[0-9a-fA-F]{64}", self.blockchain_signer_private_key.get_secret_value()):
            raise ValueError("LEDGERCHAIN_BLOCKCHAIN_SIGNER_PRIVATE_KEY must be a 32-byte hex key")


@lru_cache
def get_settings() -> Settings:
    return Settings()
