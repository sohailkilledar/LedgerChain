from app.blockchain.provider import (
    AnchorPayload,
    BlockchainProviderError,
    ProviderAnchor,
    ProviderHealth,
    ProviderTransaction,
)


class DevelopmentBlockchainProvider:
    """Explicitly simulated provider; never creates a blockchain transaction hash."""

    provider_id = "development"

    def __init__(self, network: str) -> None:
        self.network = network

    def anchor_ledger_transaction(
        self, payload: AnchorPayload, *, idempotency_key: str
    ) -> ProviderTransaction:
        return ProviderTransaction(status="simulated")

    def get_transaction(self, transaction_hash: str) -> ProviderTransaction | None:
        return None

    def verify_anchor(self, digest: str) -> ProviderAnchor | None:
        return None

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(status="simulated")


class UnavailableBlockchainProvider:
    """Safe placeholder when config selects a provider not implemented by this module."""

    def __init__(self, provider_id: str, network: str) -> None:
        self.provider_id = provider_id
        self.network = network

    def anchor_ledger_transaction(
        self, payload: AnchorPayload, *, idempotency_key: str
    ) -> ProviderTransaction:
        raise BlockchainProviderError("PROVIDER_UNAVAILABLE")

    def get_transaction(self, transaction_hash: str) -> ProviderTransaction | None:
        raise BlockchainProviderError("PROVIDER_UNAVAILABLE")

    def verify_anchor(self, digest: str) -> ProviderAnchor | None:
        raise BlockchainProviderError("PROVIDER_UNAVAILABLE")

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(status="unavailable")


__all__ = ["DevelopmentBlockchainProvider", "UnavailableBlockchainProvider"]
