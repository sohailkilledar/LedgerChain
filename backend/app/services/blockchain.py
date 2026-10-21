from datetime import datetime, timezone
from hashlib import sha256
import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.blockchain.development import DevelopmentBlockchainProvider, UnavailableBlockchainProvider
from app.blockchain.evm import EVMBlockchainProvider
from app.blockchain.provider import (
    ASSET_EVENT_DIGEST_VERSION,
    SHIPMENT_EVENT_DIGEST_VERSION,
    ProviderAnchor,
    AnchorPayload,
    BlockchainProvider,
    DIGEST_VERSION,
    BlockchainProviderError,
    ProviderHealth,
    ProviderTransaction,
)
from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError, ServiceUnavailableError
from app.models.account import OrganizationMembership
from app.models.asset import Asset, AssetEvent
from app.models.auth import User
from app.models.blockchain import BlockchainRecord
from app.models.supply_chain import InventoryShipment, InventoryShipmentEvent
from app.models.ledger import LedgerEntry, LedgerTransaction
from app.repositories.asset import AssetRepository
from app.repositories.blockchain import BlockchainRepository
from app.repositories.ledger import LedgerRepository
from app.schemas.blockchain import (
    BlockchainRecordResponse,
    BlockchainStatusResponse,
    BlockchainVerificationResponse,
    ShipmentEventVerificationResponse,
)

logger = logging.getLogger("app.blockchain")
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "submitting": frozenset({"submitted", "confirmed", "simulated", "submission_failed"}),
    "submission_failed": frozenset({"submitting"}),
    "submitted": frozenset({"confirmed", "failed"}),
    "confirmed": frozenset(),
    "failed": frozenset(),
    "simulated": frozenset(),
}


def canonical_ledger_payload(transaction: LedgerTransaction, entries: list[LedgerEntry]) -> bytes:
    raise ServiceUnavailableError(
        "This workflow is intentionally unavailable in the public source release. "
        "The deployed LedgerChain application is separate from this source distribution.",
        code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
        retryable=False,
    )


def ledger_digest(transaction: LedgerTransaction, entries: list[LedgerEntry]) -> str:
    raise ServiceUnavailableError(
        "This workflow is intentionally unavailable in the public source release. "
        "The deployed LedgerChain application is separate from this source distribution.",
        code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
        retryable=False,
    )


def canonical_asset_event_payload(event: AssetEvent) -> bytes:
    raise ServiceUnavailableError(
        "This workflow is intentionally unavailable in the public source release. "
        "The deployed LedgerChain application is separate from this source distribution.",
        code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
        retryable=False,
    )


def asset_event_digest(event: AssetEvent) -> str:
    raise ServiceUnavailableError(
        "This workflow is intentionally unavailable in the public source release. "
        "The deployed LedgerChain application is separate from this source distribution.",
        code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
        retryable=False,
    )


def canonical_shipment_event_payload(event: InventoryShipmentEvent) -> bytes:
    raise ServiceUnavailableError(
        "This workflow is intentionally unavailable in the public source release. "
        "The deployed LedgerChain application is separate from this source distribution.",
        code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
        retryable=False,
    )


def shipment_event_digest(event: InventoryShipmentEvent) -> str:
    raise ServiceUnavailableError(
        "This workflow is intentionally unavailable in the public source release. "
        "The deployed LedgerChain application is separate from this source distribution.",
        code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
        retryable=False,
    )


class BlockchainService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        provider: BlockchainProvider | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.ledger = LedgerRepository(session)
        self.records = BlockchainRepository(session)
        if provider is not None:
            self.provider = provider
        elif settings.blockchain_provider == "development":
            self.provider = DevelopmentBlockchainProvider(settings.blockchain_network)
        elif settings.blockchain_provider == "evm" and settings.blockchain_enabled:
            self.provider = EVMBlockchainProvider(settings)
        else:
            self.provider = UnavailableBlockchainProvider(
                settings.blockchain_provider, settings.blockchain_network
            )

    def status(self) -> BlockchainStatusResponse:
        if not self.settings.blockchain_enabled:
            health = "disabled"
        else:
            try:
                health = self.provider.health_check().status
            except Exception as exc:
                logger.warning(
                    "blockchain_health_check_failed",
                    extra={"provider": self.provider.provider_id, "exception_type": type(exc).__name__},
                )
                health = "unavailable"
        return BlockchainStatusResponse(
            enabled=self.settings.blockchain_enabled,
            provider=self.provider.provider_id,
            network=self.settings.blockchain_network,
            chain_id=self.settings.blockchain_chain_id,
            contract_address=(self.settings.blockchain_contract_address if self.provider.provider_id == "evm" else None),
            contract_version=(self.settings.blockchain_contract_version if self.provider.provider_id == "evm" else None),
            health=health,
        )

    def anchor(self, ledger_transaction_id: UUID, user: User) -> BlockchainRecordResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def anchor_asset_event(self, asset_event_id: UUID, user: User) -> BlockchainRecordResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def anchor_shipment_event(self, shipment_event_id: UUID, user: User) -> BlockchainRecordResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def verify_shipment_event(self, shipment_event_id: UUID, user: User) -> ShipmentEventVerificationResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def _verify_shipment_anchor(self, event: InventoryShipmentEvent, record: BlockchainRecord, digest: str) -> tuple[str, bool]:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def verify_asset_event(self, asset_event_id: UUID, user: User) -> dict[str, object]:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def verify(self, ledger_transaction_id: UUID, user: User) -> BlockchainVerificationResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    @staticmethod
    def _verification_result(
        transaction_id: UUID,
        current_digest: str,
        record: BlockchainRecord,
        result: str,
        *,
        integrity_warning: bool = False,
    ) -> BlockchainVerificationResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def get_record(self, record_id: UUID, user: User) -> BlockchainRecordResponse:
        record = self.records.get(record_id)
        if record is None:
            raise NotFoundError("The blockchain record was not found.", code="BLOCKCHAIN_RECORD_NOT_FOUND")
        if record.asset_event_id is not None:
            self._authorized_asset_event(record.asset_event_id, user)
        elif record.shipment_event_id is not None:
            self._authorized_shipment_event(record.shipment_event_id, user)
        elif record.ledger_transaction_id is not None:
            self._authorized_ledger_transaction(record.ledger_transaction_id, user)
        else:
            raise NotFoundError("The blockchain record was not found.", code="BLOCKCHAIN_RECORD_NOT_FOUND")
        if (
            self.settings.blockchain_enabled
            and record.provider == self.provider.provider_id
            and record.network == self.settings.blockchain_network
            and record.chain_id == self.settings.blockchain_chain_id
            and record.status == "submitted"
            and record.transaction_hash
        ):
            try:
                result = self.provider.get_transaction(record.transaction_hash)
                if result is not None:
                    if result.transaction_hash != record.transaction_hash:
                        raise BlockchainProviderError("PROVIDER_INVALID_RESPONSE")
                    self._apply_provider_result(record, result)
                    self.session.commit()
            except Exception as exc:
                self.session.rollback()
                logger.warning(
                    "blockchain_status_refresh_failed",
                    extra={"provider": self.provider.provider_id, "exception_type": type(exc).__name__},
                )
        return BlockchainRecordResponse.model_validate(record)

    @staticmethod
    def transition(record: BlockchainRecord, target: str) -> None:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def _authorized_asset_event(
        self, asset_event_id: UUID, user: User, *, require_owner: bool = False
    ) -> tuple[AssetEvent, Asset]:
        event = self.session.get(AssetEvent, asset_event_id)
        if event is None:
            raise NotFoundError("The asset event was not found.", code="ASSET_EVENT_NOT_FOUND")
        asset = self.session.get(Asset, event.asset_id)
        if asset is None or not AssetRepository(self.session).accessible(asset, user.id):
            raise NotFoundError("The asset event was not found.", code="ASSET_EVENT_NOT_FOUND")
        if require_owner:
            membership = self.session.scalar(
                select(OrganizationMembership).where(
                    OrganizationMembership.user_id == user.id,
                    OrganizationMembership.organization_id == asset.current_owner_organization_id,
                )
            )
            if membership is None or membership.role != "owner":
                raise NotFoundError("The asset event was not found.", code="ASSET_EVENT_NOT_FOUND")
        return event, asset

    def _authorized_shipment_event(
        self, shipment_event_id: UUID, user: User, *, require_owner: bool = False
    ) -> tuple[InventoryShipmentEvent, InventoryShipment]:
        event = self.session.get(InventoryShipmentEvent, shipment_event_id)
        if event is None:
            raise NotFoundError("The shipment event was not found.", code="SHIPMENT_EVENT_NOT_FOUND")
        shipment = self.session.get(InventoryShipment, event.shipment_id)
        if shipment is None:
            raise NotFoundError("The shipment event was not found.", code="SHIPMENT_EVENT_NOT_FOUND")
        statement = select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id.in_(
                [shipment.sender_organization_id, shipment.recipient_organization_id]
            ),
        )
        if require_owner:
            statement = statement.where(OrganizationMembership.role == "owner")
        if self.session.scalar(statement) is None:
            raise NotFoundError("The shipment event was not found.", code="SHIPMENT_EVENT_NOT_FOUND")
        return event, shipment

    def _authorized_ledger_transaction(self, transaction_id: UUID, user: User) -> LedgerTransaction:
        found = self.ledger.get_with_payment(transaction_id)
        if found is None:
            raise NotFoundError("The ledger transaction was not found.", code="LEDGER_TRANSACTION_NOT_FOUND")
        transaction, payment = found
        allowed = payment.sender_user_id == user.id or self.ledger.has_membership(
            user.id, payment.sender_organization_id
        ) or self.ledger.has_membership(user.id, payment.recipient_organization_id)
        if not allowed:
            raise NotFoundError("The ledger transaction was not found.", code="LEDGER_TRANSACTION_NOT_FOUND")
        return transaction

    def _apply_provider_result(self, record: BlockchainRecord, result: ProviderTransaction) -> None:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def _mark_failed(self, record: BlockchainRecord, code: str) -> None:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )


__all__ = [
    "BlockchainService",
    "DIGEST_VERSION",
    "canonical_ledger_payload",
    "canonical_shipment_event_payload",
    "ledger_digest",
    "shipment_event_digest",
]
