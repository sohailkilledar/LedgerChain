from decimal import Decimal
from hashlib import sha256
import json
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AuthorizationError, ConflictError, NotFoundError, ValidationError
from app.models.account import OrganizationMembership
from app.models.asset import Product
from app.models.auth import User
from app.models.inventory import InventoryMovement, InventoryStock
from app.models.supply_chain import InventoryBatch
from app.repositories.inventory import InventoryRepository
from app.schemas.inventory import InventoryMovementCreate, InventoryMovementResponse, InventoryStockResponse

_IDEMPOTENCY_KEY = re.compile(r"^[\x21-\x7e]{1,128}$")
_ZERO = Decimal("0")
_MAX_QUANTITY = Decimal("999999999999999.999")


class InventoryService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.inventory = InventoryRepository(session)

    def stocks(self, user: User, *, limit: int, offset: int) -> tuple[list[InventoryStockResponse], bool]:
        rows = self.inventory.stocks_for_user(user.id, limit=limit + 1, offset=offset)
        items = [self._stock_response(stock, product, batch) for stock, product, batch in rows[:limit]]
        return items, len(rows) > limit

    def movements(self, user: User, *, limit: int, offset: int) -> tuple[list[InventoryMovementResponse], bool]:
        rows = self.inventory.movements_for_user(user.id, limit=limit + 1, offset=offset)
        items = [self._movement_response(movement, product, batch) for movement, product, batch in rows[:limit]]
        return items, len(rows) > limit

    def create_movement(
        self, user: User, request: InventoryMovementCreate, idempotency_key: str
    ) -> InventoryMovementResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def _get_or_create_stock(
        self, organization_id: UUID, product_id: UUID, location: str, batch_id: UUID | None = None
    ) -> InventoryStock:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def _membership(self, user_id: UUID, organization_id: UUID) -> OrganizationMembership:
        membership = self.session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == organization_id,
            )
        )
        if membership is None:
            raise NotFoundError("The organization was not found.", code="ORGANIZATION_NOT_FOUND")
        return membership

    def _idempotent_movement(self, organization_id: UUID, key: str) -> InventoryMovement | None:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def _replay(self, movement: InventoryMovement, fingerprint: str) -> InventoryMovementResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    @staticmethod
    def _validate_idempotency_key(key: str) -> None:
        if not _IDEMPOTENCY_KEY.fullmatch(key):
            raise ValidationError("The idempotency key must contain 1–128 printable ASCII characters.", code="INVALID_IDEMPOTENCY_KEY")

    @staticmethod
    def _fingerprint(payload: dict[str, object]) -> str:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    @staticmethod
    def _stock_response(stock: InventoryStock, product: Product, batch: InventoryBatch | None) -> InventoryStockResponse:
        threshold = stock.low_stock_threshold
        return InventoryStockResponse(
            id=stock.id,
            organization_id=stock.organization_id,
            product_id=stock.product_id,
            sku=product.sku,
            product_name=product.name,
            unit=product.unit,
            batch_id=stock.batch_id,
            batch_code=batch.batch_code if batch is not None else None,
            location=stock.location,
            quantity=stock.quantity,
            low_stock_threshold=threshold,
            is_low_stock=threshold is not None and stock.quantity <= threshold,
            updated_at=stock.updated_at,
        )

    @staticmethod
    def _movement_response(
        movement: InventoryMovement, product: Product, batch: InventoryBatch | None
    ) -> InventoryMovementResponse:
        return InventoryMovementResponse(
            id=movement.id,
            organization_id=movement.organization_id,
            product_id=movement.product_id,
            sku=product.sku,
            product_name=product.name,
            unit=product.unit,
            batch_id=movement.batch_id,
            batch_code=batch.batch_code if batch is not None else None,
            actor_user_id=movement.actor_user_id,
            movement_type=movement.movement_type,
            source_location=movement.source_location,
            destination_location=movement.destination_location,
            quantity=movement.quantity,
            adjustment_delta=movement.adjustment_delta,
            reason=movement.reason,
            source_quantity_before=movement.source_quantity_before,
            source_quantity_after=movement.source_quantity_after,
            destination_quantity_before=movement.destination_quantity_before,
            destination_quantity_after=movement.destination_quantity_after,
            created_at=movement.created_at,
        )


__all__ = ["InventoryService"]
