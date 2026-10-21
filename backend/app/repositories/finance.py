from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import OrganizationMembership
from app.models.finance import FinanceBudget, PaymentRequest, PaymentRequestEvent


class FinanceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def memberships(self, user_id: UUID) -> list[OrganizationMembership]:
        return list(self.session.scalars(select(OrganizationMembership).where(OrganizationMembership.user_id == user_id)).all())

    def request(self, request_id: UUID) -> PaymentRequest | None:
        return self.session.scalar(select(PaymentRequest).where(PaymentRequest.id == request_id))

    def requests_for_organizations(self, organization_ids: list[UUID], *, limit: int, offset: int) -> list[PaymentRequest]:
        if not organization_ids:
            return []
        statement = (
            select(PaymentRequest)
            .where(PaymentRequest.organization_id.in_(organization_ids))
            .order_by(PaymentRequest.created_at.desc(), PaymentRequest.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement).all())

    def events(self, request_id: UUID) -> list[PaymentRequestEvent]:
        statement = select(PaymentRequestEvent).where(PaymentRequestEvent.payment_request_id == request_id).order_by(PaymentRequestEvent.sequence_number)
        return list(self.session.scalars(statement).all())

    def budgets_for_organizations(self, organization_ids: list[UUID], *, limit: int, offset: int) -> list[FinanceBudget]:
        if not organization_ids:
            return []
        statement = (
            select(FinanceBudget)
            .where(FinanceBudget.organization_id.in_(organization_ids))
            .order_by(FinanceBudget.period_start.desc(), FinanceBudget.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement).all())


__all__ = ["FinanceRepository"]
