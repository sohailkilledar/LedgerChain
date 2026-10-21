from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

DIGEST_VERSION = "ledgerchain-ledger-v1"
ASSET_EVENT_DIGEST_VERSION = "ledgerchain-asset-event-v1"
SHIPMENT_EVENT_DIGEST_VERSION = "ledgerchain-shipment-event-v1"
SUPPORTED_DIGEST_VERSIONS = frozenset({DIGEST_VERSION, ASSET_EVENT_DIGEST_VERSION, SHIPMENT_EVENT_DIGEST_VERSION})


@dataclass(frozen=True)
class AnchorPayload:
    reference_id: UUID
    digest_version: str
    digest: str

    @property
    def ledger_transaction_id(self) -> UUID:
        """Compatibility alias for Module 7/8 integrations."""
        return self.reference_id


@dataclass(frozen=True)
class ProviderTransaction:
    status: Literal["submitted", "confirmed", "failed", "simulated"]
    transaction_hash: str | None = None
    block_number: int | None = None
    submitted_at: datetime | None = None
    confirmed_at: datetime | None = None
    failure_code: str | None = None
    contract_address: str | None = None
    contract_version: str | None = None


@dataclass(frozen=True)
class ProviderAnchor:
    digest: str
    reference_id: str
    anchored_at: datetime
    submitter: str


@dataclass(frozen=True)
class ProviderHealth:
    status: Literal["available", "simulated", "unavailable"]


class BlockchainProviderError(Exception):
    _SAFE_CODES = frozenset(
        {
            "PROVIDER_UNAVAILABLE",
            "PROVIDER_TIMEOUT",
            "PROVIDER_SUBMISSION_FAILED",
            "PROVIDER_INVALID_RESPONSE",
        }
    )

    def __init__(self, code: str = "PROVIDER_SUBMISSION_FAILED") -> None:
        self.code = code if code in self._SAFE_CODES else "PROVIDER_SUBMISSION_FAILED"
        super().__init__(self.code)


class BlockchainProvider(Protocol):
    provider_id: str
    network: str

    def anchor_ledger_transaction(
        self, payload: AnchorPayload, *, idempotency_key: str
    ) -> ProviderTransaction: ...

    def get_transaction(self, transaction_hash: str) -> ProviderTransaction | None: ...

    def verify_anchor(self, digest: str) -> ProviderAnchor | None: ...

    def health_check(self) -> ProviderHealth: ...


__all__ = [
    "AnchorPayload",
    "BlockchainProvider",
    "BlockchainProviderError",
    "ProviderHealth",
    "ProviderTransaction",
]
