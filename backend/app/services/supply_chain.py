from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AuthorizationError, ConflictError, NotFoundError, ValidationError
from app.models.account import Organization, OrganizationMembership
from app.models.asset import Product
from app.models.auth import User
from app.models.blockchain import BlockchainRecord
from app.models.inventory import InventoryMovement, InventoryStock
from app.models.supply_chain import InventoryBatch, InventoryShipment, InventoryShipmentEvent
from app.schemas.blockchain import BlockchainRecordResponse
from app.schemas.supply_chain import (
    InventoryBatchCreate,
    InventoryBatchResponse,
    InventoryShipmentCreate,
    InventoryShipmentEventResponse,
    InventoryShipmentReceive,
    InventoryShipmentResponse,
    InventoryShipmentReject,
)

_KEY = re.compile(r"^[\x21-\x7e]{1,128}$")


class SupplyChainService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_batches(self, user: User, *, limit: int, offset: int) -> tuple[list[InventoryBatchResponse], bool]:
        organization_ids = self._organization_ids(user.id)
        statement = (
            select(InventoryBatch, Product)
            .join(Product, Product.id == InventoryBatch.product_id)
            .where(InventoryBatch.organization_id.in_(organization_ids))
            .order_by(InventoryBatch.created_at.desc(), InventoryBatch.id.desc())
            .offset(offset)
            .limit(limit + 1)
        )
        rows = self.session.execute(statement).all()
        return [self._batch_response(batch, product) for batch, product in rows[:limit]], len(rows) > limit

    def create_batch(self, user: User, request: InventoryBatchCreate) -> InventoryBatchResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def list_shipments(self, user: User, *, limit: int, offset: int) -> tuple[list[InventoryShipmentResponse], bool]:
        organization_ids = self._organization_ids(user.id)
        from sqlalchemy.orm import aliased

        sender = aliased(Organization)
        recipient = aliased(Organization)
        statement = (
            select(InventoryShipment, sender, recipient, Product, InventoryBatch)
            .join(sender, sender.id == InventoryShipment.sender_organization_id)
            .join(recipient, recipient.id == InventoryShipment.recipient_organization_id)
            .join(Product, Product.id == InventoryShipment.product_id)
            .join(InventoryBatch, InventoryBatch.id == InventoryShipment.batch_id)
            .where(
                (InventoryShipment.sender_organization_id.in_(organization_ids))
                | (InventoryShipment.recipient_organization_id.in_(organization_ids))
            )
            .order_by(InventoryShipment.created_at.desc(), InventoryShipment.id.desc())
            .offset(offset)
            .limit(limit + 1)
        )
        rows = self.session.execute(statement).all()
        shipments = rows[:limit]
        shipment_ids = [row[0].id for row in shipments]
        events = self.session.scalars(
            select(InventoryShipmentEvent)
            .where(InventoryShipmentEvent.shipment_id.in_(shipment_ids))
            .order_by(InventoryShipmentEvent.shipment_id, InventoryShipmentEvent.sequence_number)
        ).all() if shipment_ids else []
        by_shipment: dict[UUID, list[InventoryShipmentEvent]] = {}
        for event in events:
            by_shipment.setdefault(event.shipment_id, []).append(event)
        anchor_records = self._anchor_records_for_events(events)
        items = [
            self._shipment_response(
                shipment, sender_org, recipient_org, product, batch,
                by_shipment.get(shipment.id, []), anchor_records,
            )
            for shipment, sender_org, recipient_org, product, batch in shipments
        ]
        return items, len(rows) > limit

    def create_shipment(
        self, user: User, request: InventoryShipmentCreate, idempotency_key: str
    ) -> InventoryShipmentResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def transition(
        self,
        user: User,
        shipment_id: UUID,
        action: str,
        idempotency_key: str,
        *,
        receive: InventoryShipmentReceive | None = None,
        reject: InventoryShipmentReject | None = None,
    ) -> InventoryShipmentResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def _append_event(
        self,
        shipment: InventoryShipment,
        user: User,
        actor_organization_id: UUID,
        from_status: str | None,
        to_status: str,
        detail: str | None,
        idempotency_key: str,
        fingerprint: str,
    ) -> None:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def _get_stock(self, organization_id: UUID, product_id: UUID, location: str, batch_id: UUID, *, locked: bool = False) -> InventoryStock | None:
        statement = select(InventoryStock).where(
            InventoryStock.organization_id == organization_id,
            InventoryStock.product_id == product_id,
            InventoryStock.location == location,
            InventoryStock.batch_id == batch_id,
        )
        if locked:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def _get_or_create_stock(self, organization_id: UUID, product_id: UUID, location: str, batch_id: UUID) -> InventoryStock:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def _load_shipment_response(self, shipment: InventoryShipment) -> InventoryShipmentResponse:
        sender = self.session.get(Organization, shipment.sender_organization_id)
        recipient = self.session.get(Organization, shipment.recipient_organization_id)
        product = self.session.get(Product, shipment.product_id)
        batch = self.session.get(InventoryBatch, shipment.batch_id)
        if sender is None or recipient is None or product is None or batch is None:
            raise NotFoundError("Shipment traceability records are incomplete.", code="SHIPMENT_NOT_FOUND")
        events = self.session.scalars(
            select(InventoryShipmentEvent)
            .where(InventoryShipmentEvent.shipment_id == shipment.id)
            .order_by(InventoryShipmentEvent.sequence_number)
        ).all()
        return self._shipment_response(
            shipment, sender, recipient, product, batch, events, self._anchor_records_for_events(events)
        )

    def _anchor_records_for_events(self, events: list[InventoryShipmentEvent]) -> dict[UUID, BlockchainRecord]:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    @staticmethod
    def _batch_response(batch: InventoryBatch, product: Product) -> InventoryBatchResponse:
        return InventoryBatchResponse(
            id=batch.id,
            organization_id=batch.organization_id,
            product_id=batch.product_id,
            sku=product.sku,
            product_name=product.name,
            unit=product.unit,
            batch_code=batch.batch_code,
            manufactured_on=batch.manufactured_on,
            expires_on=batch.expires_on,
            notes=batch.notes,
            created_by_user_id=batch.created_by_user_id,
            created_at=batch.created_at,
        )

    @staticmethod
    def _shipment_response(
        shipment: InventoryShipment,
        sender: Organization,
        recipient: Organization,
        product: Product,
        batch: InventoryBatch,
        events: list[InventoryShipmentEvent],
        anchor_records: dict[UUID, BlockchainRecord],
    ) -> InventoryShipmentResponse:
        return InventoryShipmentResponse(
            id=shipment.id,
            sender_organization_id=shipment.sender_organization_id,
            sender_name=sender.name,
            sender_account_number=sender.account_number,
            recipient_organization_id=shipment.recipient_organization_id,
            recipient_name=recipient.name,
            recipient_account_number=recipient.account_number,
            product_id=shipment.product_id,
            product_name=product.name,
            sku=product.sku,
            unit=product.unit,
            batch_id=shipment.batch_id,
            batch_code=batch.batch_code,
            quantity=shipment.quantity,
            source_location=shipment.source_location,
            destination_location=shipment.destination_location,
            status=shipment.status,
            note=shipment.note,
            rejection_reason=shipment.rejection_reason,
            created_by_user_id=shipment.created_by_user_id,
            dispatcher_user_id=shipment.dispatcher_user_id,
            receiver_user_id=shipment.receiver_user_id,
            created_at=shipment.created_at,
            dispatched_at=shipment.dispatched_at,
            in_transit_at=shipment.in_transit_at,
            received_at=shipment.received_at,
            rejected_at=shipment.rejected_at,
            events=[
                InventoryShipmentEventResponse(
                    id=event.id,
                    sequence_number=event.sequence_number,
                    actor_user_id=event.actor_user_id,
                    actor_organization_id=event.actor_organization_id,
                    from_status=event.from_status,
                    to_status=event.to_status,
                    detail=event.detail,
                    created_at=event.created_at,
                    blockchain_record=(
                        BlockchainRecordResponse.model_validate(anchor_records[event.id])
                        if event.id in anchor_records else None
                    ),
                )
                for event in events
            ],
        )

    def _require_owner(self, user_id: UUID, organization_id: UUID) -> OrganizationMembership:
        membership = self.session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == organization_id,
            )
        )
        if membership is None:
            raise NotFoundError("The organization was not found.", code="ORGANIZATION_NOT_FOUND")
        if membership.role != "owner":
            raise AuthorizationError("Only an organization owner can manage batches and shipments.", code="OWNER_REQUIRED")
        return membership

    def _organization_ids(self, user_id: UUID) -> list[UUID]:
        return list(self.session.scalars(
            select(OrganizationMembership.organization_id).where(OrganizationMembership.user_id == user_id)
        ).all())

    @staticmethod
    def _validate_key(key: str) -> None:
        if not _KEY.fullmatch(key):
            raise ValidationError("The idempotency key must contain 1–128 printable ASCII characters.", code="INVALID_IDEMPOTENCY_KEY")

    @staticmethod
    def _fingerprint(payload: dict[str, object]) -> str:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )


__all__ = ["SupplyChainService"]
