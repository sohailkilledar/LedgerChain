from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session, aliased

from app.models.account import Organization, OrganizationMembership
from app.models.ledger import LedgerEntry, LedgerTransaction
from app.models.payment import Payment
from app.repositories.base import Repository


class LedgerRepository(Repository[LedgerTransaction]):
    model = LedgerTransaction

    def get_by_payment_id(self, payment_id: UUID) -> LedgerTransaction | None:
        return self.session.scalar(
            select(LedgerTransaction).where(LedgerTransaction.payment_id == payment_id)
        )

    def entries_for_transaction(self, transaction_id: UUID) -> list[LedgerEntry]:
        statement = (
            select(LedgerEntry)
            .where(LedgerEntry.ledger_transaction_id == transaction_id)
            .order_by(LedgerEntry.created_at, LedgerEntry.id)
        )
        return list(self.session.scalars(statement).all())

    def get_with_payment(self, transaction_id: UUID) -> tuple[LedgerTransaction, Payment] | None:
        row = self.session.execute(
            select(LedgerTransaction, Payment)
            .join(Payment, Payment.id == LedgerTransaction.payment_id)
            .where(LedgerTransaction.id == transaction_id)
        ).first()
        return (row[0], row[1]) if row else None

    def activity_for_user(
        self,
        user_id: UUID,
        organization_ids: list[UUID],
        *,
        activity_type: str | None,
        limit: int,
        offset: int,
    ) -> list[tuple[Payment, LedgerTransaction, Organization]]:
        sender = aliased(Organization)
        visibility = [Payment.sender_user_id == user_id]
        if organization_ids:
            visibility.extend(
                [
                    Payment.sender_organization_id.in_(organization_ids),
                    Payment.recipient_organization_id.in_(organization_ids),
                ]
            )
        statement = (
            select(Payment, LedgerTransaction, sender)
            .join(LedgerTransaction, LedgerTransaction.payment_id == Payment.id)
            .join(sender, sender.id == Payment.sender_organization_id)
            .where(or_(*visibility), Payment.status == "completed", LedgerTransaction.status == "posted")
            .order_by(desc(Payment.completed_at), desc(Payment.id))
            .offset(offset)
            .limit(limit)
        )
        if activity_type == "payment":
            statement = statement.where(LedgerTransaction.transaction_type == "payment_transfer")
        return [tuple(row) for row in self.session.execute(statement).all()]

    def balanced_totals(self, transaction_id: UUID) -> tuple[int, int, Decimal | None, Decimal | None]:
        entries = self.entries_for_transaction(transaction_id)
        debits = [entry.amount for entry in entries if entry.direction == "debit"]
        credits = [entry.amount for entry in entries if entry.direction == "credit"]
        return (
            len(debits),
            len(credits),
            sum(debits, Decimal("0.00")) if debits else None,
            sum(credits, Decimal("0.00")) if credits else None,
        )

    def has_membership(self, user_id: UUID, organization_id: UUID) -> bool:
        return self.session.scalar(
            select(OrganizationMembership.id).where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == organization_id,
            )
        ) is not None


__all__ = ["LedgerRepository"]
