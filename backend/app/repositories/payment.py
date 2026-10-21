from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.models.account import Organization, OrganizationMembership
from app.models.payment import Payment
from app.repositories.base import Repository


class PaymentRepository(Repository[Payment]):
    model = Payment

    def get_by_idempotency_key(self, sender_organization_id: UUID, key: str) -> Payment | None:
        return self.session.scalar(
            select(Payment).where(
                Payment.sender_organization_id == sender_organization_id,
                Payment.idempotency_key == key,
            )
        )

    def list_for_user(
        self, user_id: UUID, organization_ids: Sequence[UUID], *, limit: int, offset: int
    ) -> list[Payment]:
        visibility = [Payment.sender_user_id == user_id]
        if organization_ids:
            visibility.extend(
                [
                    Payment.sender_organization_id.in_(organization_ids),
                    Payment.recipient_organization_id.in_(organization_ids),
                ]
            )
        statement = (
            select(Payment)
            .where(or_(*visibility))
            .order_by(desc(Payment.created_at), desc(Payment.id))
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement).all())


class PaymentAccountRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_account_number(self, account_number: str) -> Organization | None:
        return self.session.scalar(
            select(Organization).where(Organization.account_number == account_number)
        )

    def get_for_user(self, user_id: UUID) -> tuple[Organization, OrganizationMembership] | None:
        statement = (
            select(Organization, OrganizationMembership)
            .join(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
            .where(OrganizationMembership.user_id == user_id)
            .order_by(OrganizationMembership.created_at, Organization.id)
        )
        row = self.session.execute(statement).first()
        return (row[0], row[1]) if row else None

    def get_for_user_in_organization(
        self, user_id: UUID, organization_id: UUID
    ) -> tuple[Organization, OrganizationMembership] | None:
        statement = (
            select(Organization, OrganizationMembership)
            .join(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
            .where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == organization_id,
            )
        )
        row = self.session.execute(statement).first()
        return (row[0], row[1]) if row else None

    @staticmethod
    def lock_statement(organization_ids: Sequence[UUID]):
        return (
            select(Organization)
            .where(Organization.id.in_(organization_ids))
            .order_by(Organization.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def lock_accounts(self, organization_ids: Sequence[UUID]) -> dict[UUID, Organization]:
        statement = self.lock_statement(organization_ids)
        return {organization.id: organization for organization in self.session.scalars(statement).all()}

    def organization_ids_for_user(self, user_id: UUID) -> list[UUID]:
        statement = select(OrganizationMembership.organization_id).where(
            OrganizationMembership.user_id == user_id
        )
        return list(self.session.scalars(statement).all())

    def user_is_member(self, user_id: UUID, organization_id: UUID) -> bool:
        statement = select(OrganizationMembership.id).where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.organization_id == organization_id,
        )
        return self.session.scalar(statement) is not None


__all__ = ["PaymentAccountRepository", "PaymentRepository"]
