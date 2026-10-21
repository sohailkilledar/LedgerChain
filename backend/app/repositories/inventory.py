from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import OrganizationMembership
from app.models.asset import Product
from app.models.auth import User
from app.models.inventory import InventoryMovement, InventoryStock
from app.models.supply_chain import InventoryBatch
from app.repositories.base import Repository


class InventoryRepository(Repository[InventoryStock]):
    model = InventoryStock

    def organization_ids(self, user_id: UUID) -> list[UUID]:
        return list(
            self.session.scalars(
                select(OrganizationMembership.organization_id).where(OrganizationMembership.user_id == user_id)
            ).all()
        )

    def stock_at(
        self, organization_id: UUID, product_id: UUID, location: str, *, batch_id: UUID | None = None, locked: bool = False
    ) -> InventoryStock | None:
        statement = select(InventoryStock).where(
            InventoryStock.organization_id == organization_id,
            InventoryStock.product_id == product_id,
            InventoryStock.location == location,
            InventoryStock.batch_id == batch_id,
        )
        if locked:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def stocks_for_user(self, user_id: UUID, *, limit: int, offset: int) -> list[tuple[InventoryStock, Product, InventoryBatch | None]]:
        organization_ids = self.organization_ids(user_id)
        if not organization_ids:
            return []
        return [
            tuple(row)
            for row in self.session.execute(
                select(InventoryStock, Product, InventoryBatch)
                .join(Product, Product.id == InventoryStock.product_id)
                .outerjoin(InventoryBatch, InventoryBatch.id == InventoryStock.batch_id)
                .where(InventoryStock.organization_id.in_(organization_ids))
                .order_by(Product.name, InventoryStock.location, InventoryBatch.batch_code, InventoryStock.id)
                .offset(offset)
                .limit(limit)
            ).all()
        ]

    def movements_for_user(self, user_id: UUID, *, limit: int, offset: int) -> list[tuple[InventoryMovement, Product, InventoryBatch | None]]:
        organization_ids = self.organization_ids(user_id)
        if not organization_ids:
            return []
        return [
            tuple(row)
            for row in self.session.execute(
                select(InventoryMovement, Product, InventoryBatch)
                .join(Product, Product.id == InventoryMovement.product_id)
                .outerjoin(InventoryBatch, InventoryBatch.id == InventoryMovement.batch_id)
                .where(InventoryMovement.organization_id.in_(organization_ids))
                .order_by(InventoryMovement.created_at.desc(), InventoryMovement.id.desc())
                .offset(offset)
                .limit(limit)
            ).all()
        ]

    def movements_for_activity(self, organization_ids: list[UUID], *, limit: int) -> list[tuple[InventoryMovement, Product, User]]:
        if not organization_ids:
            return []
        return [
            tuple(row)
            for row in self.session.execute(
                select(InventoryMovement, Product, User)
                .join(Product, Product.id == InventoryMovement.product_id)
                .join(User, User.id == InventoryMovement.actor_user_id)
                .where(InventoryMovement.organization_id.in_(organization_ids))
                .order_by(InventoryMovement.created_at.desc(), InventoryMovement.id.desc())
                .limit(limit)
            ).all()
        ]


__all__ = ["InventoryRepository"]
