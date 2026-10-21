from collections.abc import Iterator
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.account import OrganizationMembership
from app.models.asset import Asset, AssetEvent, AssetOwnership, Product
from app.models.auth import User
from app.repositories.base import Repository


class AssetRepository(Repository[Asset]):
    model = Asset

    def get_locked(self, asset_id: UUID) -> Asset | None:
        return self.session.scalar(select(Asset).where(Asset.id == asset_id).with_for_update())

    def accessible(self, asset: Asset, user_id: UUID) -> bool:
        organization_ids = self.organization_ids(user_id)
        return any(
            organization_id in organization_ids
            for organization_id in (
                asset.organization_id,
                asset.current_owner_organization_id,
                asset.current_custodian_organization_id,
            )
            if organization_id is not None
        )

    def organization_ids(self, user_id: UUID) -> set[UUID]:
        return set(
            self.session.scalars(
                select(OrganizationMembership.organization_id).where(OrganizationMembership.user_id == user_id)
            ).all()
        )

    def products_for_user(self, user_id: UUID, *, limit: int, offset: int) -> list[Product]:
        organization_ids = self.organization_ids(user_id)
        if not organization_ids:
            return []
        return list(
            self.session.scalars(
                select(Product)
                .where(Product.organization_id.in_(organization_ids))
                .order_by(Product.created_at.desc(), Product.id)
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def product_visible(self, product: Product, user_id: UUID) -> bool:
        return product.organization_id in self.organization_ids(user_id)

    def list_assets_for_user(self, user_id: UUID, *, limit: int, offset: int) -> list[Asset]:
        organization_ids = self.organization_ids(user_id)
        if not organization_ids:
            return []
        return list(
            self.session.scalars(
                select(Asset)
                .where(
                    or_(
                        Asset.organization_id.in_(organization_ids),
                        Asset.current_owner_organization_id.in_(organization_ids),
                        Asset.current_custodian_organization_id.in_(organization_ids),
                    )
                )
                .order_by(Asset.created_at.desc(), Asset.id)
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def events_for_asset(self, asset_id: UUID, *, limit: int, offset: int) -> tuple[list[AssetEvent], bool]:
        rows = list(
            self.session.scalars(
                select(AssetEvent)
                .where(AssetEvent.asset_id == asset_id)
                .order_by(AssetEvent.sequence_number)
                .offset(offset)
                .limit(limit + 1)
            ).all()
        )
        return rows[:limit], len(rows) > limit

    def iter_events_for_asset(self, asset_id: UUID) -> Iterator[AssetEvent]:
        return iter(
            self.session.scalars(
                select(AssetEvent).where(AssetEvent.asset_id == asset_id).order_by(AssetEvent.sequence_number)
            ).yield_per(100)
        )

    def events_for_activity(self, organization_ids: list[UUID], *, limit: int) -> list[tuple[AssetEvent, Asset, User]]:
        if not organization_ids:
            return []
        return [
            tuple(row)
            for row in self.session.execute(
                select(AssetEvent, Asset, User)
                .join(Asset, Asset.id == AssetEvent.asset_id)
                .join(User, User.id == AssetEvent.actor_user_id)
                .where(
                    or_(
                        Asset.organization_id.in_(organization_ids),
                        Asset.current_owner_organization_id.in_(organization_ids),
                        Asset.current_custodian_organization_id.in_(organization_ids),
                        AssetEvent.actor_organization_id.in_(organization_ids),
                    )
                )
                .order_by(AssetEvent.created_at.desc(), AssetEvent.id.desc())
                .limit(limit)
            ).all()
        ]

    def get_event(self, event_id: UUID) -> AssetEvent | None:
        return self.session.get(AssetEvent, event_id)

    def ownership_for_asset(self, asset_id: UUID, *, limit: int, offset: int) -> tuple[list[AssetOwnership], bool]:
        rows = list(
            self.session.scalars(
                select(AssetOwnership)
                .join(AssetEvent, AssetEvent.id == AssetOwnership.event_id)
                .where(AssetOwnership.asset_id == asset_id)
                .order_by(AssetEvent.sequence_number)
                .offset(offset)
                .limit(limit + 1)
            ).all()
        )
        return rows[:limit], len(rows) > limit

    def iter_ownership_for_asset(self, asset_id: UUID) -> Iterator[tuple[AssetOwnership, int]]:
        return iter(
            self.session.execute(
                select(AssetOwnership, AssetEvent.sequence_number)
                .join(AssetEvent, AssetEvent.id == AssetOwnership.event_id)
                .where(AssetOwnership.asset_id == asset_id)
                .order_by(AssetEvent.sequence_number)
            ).yield_per(100)
        )

    def idempotent_event_for_user(self, asset_id: UUID, user_id: UUID, key: str) -> AssetEvent | None:
        organization_ids = self.organization_ids(user_id)
        if not organization_ids:
            return None
        return self.session.scalar(
            select(AssetEvent).where(
                AssetEvent.asset_id == asset_id,
                AssetEvent.actor_organization_id.in_(organization_ids),
                AssetEvent.idempotency_key == key,
            )
        )


class ProductRepository(Repository[Product]):
    model = Product


__all__ = ["AssetRepository", "ProductRepository"]


