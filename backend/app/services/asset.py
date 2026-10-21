from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AuthorizationError, ConflictError, NotFoundError, ValidationError
from app.models.account import Organization, OrganizationMembership
from app.models.asset import Asset, AssetEvent, AssetOwnership, Product
from app.models.blockchain import BlockchainRecord
from app.models.auth import User
from app.repositories.asset import AssetRepository, ProductRepository
from app.schemas.asset import AssetCreate, AssetTransfer, CustodyChange, ProductCreate

_IDEMPOTENCY_KEY = re.compile(r"^[\x21-\x7e]{1,128}$")


class AssetService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.assets = AssetRepository(session)
        self.products = ProductRepository(session)

    def create_product(self, user: User, request: ProductCreate) -> Product:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def list_products(self, user: User, *, limit: int, offset: int) -> tuple[list[Product], bool]:
        rows = self.assets.products_for_user(user.id, limit=limit + 1, offset=offset)
        return rows[:limit], len(rows) > limit

    def get_product(self, product_id: UUID, user: User) -> Product:
        product = self.products.get(product_id)
        if product is None or not self.assets.product_visible(product, user.id):
            raise NotFoundError("The product was not found.", code="PRODUCT_NOT_FOUND")
        return product

    def create_asset(self, user: User, request: AssetCreate) -> Asset:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def list_assets(self, user: User, *, limit: int, offset: int) -> tuple[list[Asset], bool]:
        rows = self.assets.list_assets_for_user(user.id, limit=limit + 1, offset=offset)
        return rows[:limit], len(rows) > limit

    def get_asset(self, asset_id: UUID, user: User) -> Asset:
        asset = self.assets.get(asset_id)
        if asset is None or not self.assets.accessible(asset, user.id):
            raise NotFoundError("The asset was not found.", code="ASSET_NOT_FOUND")
        return asset

    def transfer(self, asset_id: UUID, user: User, request: AssetTransfer, idempotency_key: str) -> AssetEvent:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def change_custody(self, asset_id: UUID, user: User, request: CustodyChange, idempotency_key: str) -> AssetEvent:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def retire(self, asset_id: UUID, user: User, idempotency_key: str) -> AssetEvent:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def history(self, asset_id: UUID, user: User, *, limit: int, offset: int) -> tuple[list[AssetEvent], bool]:
        asset = self.get_asset(asset_id, user)
        return self.assets.events_for_asset(asset.id, limit=limit, offset=offset)

    def ownership_history(
        self, asset_id: UUID, user: User, *, limit: int, offset: int
    ) -> tuple[list[AssetOwnership], bool]:
        asset = self.get_asset(asset_id, user)
        return self.assets.ownership_for_asset(asset.id, limit=limit, offset=offset)

    def event(self, event_id: UUID, user: User) -> AssetEvent:
        event = self.assets.get_event(event_id)
        if event is None:
            raise NotFoundError("The asset event was not found.", code="ASSET_EVENT_NOT_FOUND")
        asset = self.get_asset(event.asset_id, user)
        if asset.id != event.asset_id:
            raise NotFoundError("The asset event was not found.", code="ASSET_EVENT_NOT_FOUND")
        return event

    def verification(self, asset_id: UUID, user: User) -> dict[str, object]:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def _append_event(
        self,
        asset: Asset,
        user: User,
        actor_organization_id: UUID,
        event_type: str,
        previous: dict[str, object] | None,
        resulting: dict[str, object],
        metadata: dict[str, object],
        idempotency_key: str,
        fingerprint: str,
    ) -> AssetEvent:
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

    @staticmethod
    def _state(asset: Asset) -> dict[str, object]:
        return {
            "owner": str(asset.current_owner_organization_id),
            "custodian": str(asset.current_custodian_organization_id) if asset.current_custodian_organization_id else None,
            "status": asset.status,
        }

    @staticmethod
    def _fingerprint(payload: dict[str, object]) -> str:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    @staticmethod
    def _validate_idempotency_key(value: str) -> None:
        if _IDEMPOTENCY_KEY.fullmatch(value) is None:
            raise ValidationError("Provide a valid Idempotency-Key header.", code="INVALID_ASSET_OPERATION")

    @staticmethod
    def _replay(event: AssetEvent, fingerprint: str) -> AssetEvent:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )


__all__ = ["AssetService"]


