from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import re
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AuthorizationError, ConflictError, NotFoundError, ValidationError
from app.models.account import Organization, OrganizationMembership
from app.models.auth import User
from app.models.finance import FinanceBudget, PaymentRequest, PaymentRequestEvent
from app.models.payment import Payment
from app.repositories.finance import FinanceRepository
from app.repositories.payment import PaymentAccountRepository
from app.schemas.finance import BudgetCreate, BudgetResponse, PaymentRequestCreate, PaymentRequestResponse
from app.schemas.payment import PaymentCreate
from app.services.payment import PaymentService

_PRINTABLE_KEY = re.compile(r"^[\x21-\x7e]{1,128}$")
_ACTIVE_COMMITMENTS = ("APPROVED", "PAYMENT_CREATED")
_ZERO = Decimal("0.00")


class FinanceService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = FinanceRepository(session)
        self.accounts = PaymentAccountRepository(session)

    def create_budget(self, user: User, request: BudgetCreate) -> BudgetResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def list_budgets(self, user: User, *, limit: int, offset: int) -> tuple[list[BudgetResponse], bool]:
        organization_ids = [item.organization_id for item in self.repository.memberships(user.id)]
        rows = self.repository.budgets_for_organizations(organization_ids, limit=limit + 1, offset=offset)
        budgets = rows[:limit]
        if not budgets:
            return [], len(rows) > limit
        budget_ids = [budget.id for budget in budgets]
        spent = self._amounts_by_budget(budget_ids, ("COMPLETED",))
        committed = self._amounts_by_budget(budget_ids, _ACTIVE_COMMITMENTS)
        result = [
            self._budget_response(budget, spent.get(budget.id, _ZERO), committed.get(budget.id, _ZERO))
            for budget in budgets
        ]
        return result, len(rows) > limit

    def create_request(self, user: User, request: PaymentRequestCreate, idempotency_key: str) -> PaymentRequestResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def list_requests(self, user: User, *, limit: int, offset: int) -> tuple[list[PaymentRequestResponse], bool]:
        organization_ids = [item.organization_id for item in self.repository.memberships(user.id)]
        rows = self.repository.requests_for_organizations(organization_ids, limit=limit + 1, offset=offset)
        return [self._request_response(item) for item in rows[:limit]], len(rows) > limit

    def submit_request(self, request_id: UUID, user: User) -> PaymentRequestResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def decide_request(self, request_id: UUID, user: User, *, approve: bool, note: str | None) -> PaymentRequestResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def execute_request(self, request_id: UUID, user: User) -> PaymentRequestResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def request_history(self, request_id: UUID, user: User) -> list[PaymentRequestEvent]:
        self._get_request_for_user(request_id, user)
        return self.repository.events(request_id)

    def _get_request_for_user(self, request_id: UUID, user: User, *, locked: bool = False) -> tuple[PaymentRequest, OrganizationMembership]:
        organization_ids = [item.organization_id for item in self.repository.memberships(user.id)]
        statement = select(PaymentRequest).where(PaymentRequest.id == request_id)
        if organization_ids:
            statement = statement.where(PaymentRequest.organization_id.in_(organization_ids))
        else:
            statement = statement.where(PaymentRequest.requester_user_id == user.id)
        if locked:
            statement = statement.with_for_update()
        payment_request = self.session.scalar(statement)
        if payment_request is None:
            raise NotFoundError("The payment request was not found.", code="PAYMENT_REQUEST_NOT_FOUND")
        membership = self._membership(user.id, payment_request.organization_id)
        return payment_request, membership

    def _check_budget_capacity(self, payment_request: PaymentRequest, *, include_current: bool = False) -> None:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def _amounts_by_budget(self, budget_ids: list[UUID], statuses: tuple[str, ...]) -> dict[UUID, Decimal]:
        if not budget_ids:
            return {}
        statement = (
            select(PaymentRequest.budget_id, func.sum(PaymentRequest.amount))
            .where(PaymentRequest.budget_id.in_(budget_ids), PaymentRequest.status.in_(statuses))
            .group_by(PaymentRequest.budget_id)
        )
        return {budget_id: amount for budget_id, amount in self.session.execute(statement).all() if budget_id is not None}

    @staticmethod
    def _budget_response(budget: FinanceBudget, spent: Decimal, committed: Decimal) -> BudgetResponse:
        remaining = budget.allocated_amount - spent - committed
        utilization = ((spent + committed) * Decimal("100") / budget.allocated_amount).quantize(Decimal("0.01"))
        return BudgetResponse(
            id=budget.id,
            organization_id=budget.organization_id,
            name=budget.name,
            category=budget.category,
            period_start=budget.period_start,
            period_end=budget.period_end,
            allocated_amount=budget.allocated_amount,
            spent_amount=spent,
            committed_amount=committed,
            remaining_amount=remaining,
            utilization_percent=utilization,
            currency="INR",
            status=budget.status,
            created_at=budget.created_at,
        )

    def _request_response(self, item: PaymentRequest) -> PaymentRequestResponse:
        payment = self.session.get(Payment, item.payment_id) if item.payment_id else None
        return PaymentRequestResponse(
            id=item.id,
            organization_id=item.organization_id,
            requester_user_id=item.requester_user_id,
            recipient_organization_id=item.recipient_organization_id,
            recipient_account=item.recipient_account_number,
            recipient_name=item.recipient_name,
            budget_id=item.budget_id,
            category=item.category,
            amount=item.amount,
            currency="INR",
            purpose=item.purpose,
            note=item.note,
            status=item.status,
            approver_user_id=item.approver_user_id,
            approval_note=item.approval_note,
            approved_at=item.approved_at,
            payment_id=item.payment_id,
            payment_reference=payment.reference if payment else None,
            created_at=item.created_at,
            submitted_at=item.submitted_at,
            completed_at=item.completed_at,
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
    def _require_owner(membership: OrganizationMembership) -> None:
        if membership.role != "owner":
            raise AuthorizationError("Only an organization owner can perform this finance action.", code="OWNER_REQUIRED")

    def _event(self, request: PaymentRequest, actor_id: UUID, from_status: str | None, to_status: str, detail: str | None = None) -> None:
        latest = self.session.scalar(
            select(func.max(PaymentRequestEvent.sequence_number)).where(PaymentRequestEvent.payment_request_id == request.id)
        )
        self.session.add(PaymentRequestEvent(
            payment_request_id=request.id,
            sequence_number=(latest or 0) + 1,
            actor_user_id=actor_id,
            from_status=from_status,
            to_status=to_status,
            detail=detail,
        ))

    def _transition(self, request: PaymentRequest, actor_id: UUID, target: str, detail: str | None = None) -> None:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def _commit(self) -> None:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    @staticmethod
    def _validate_idempotency_key(key: str) -> None:
        if not _PRINTABLE_KEY.fullmatch(key):
            raise ValidationError("The idempotency key must contain 1–128 printable ASCII characters.", code="INVALID_IDEMPOTENCY_KEY")

    @staticmethod
    def _fingerprint(payload: dict[str, object]) -> str:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def _replay_request(self, existing: PaymentRequest, fingerprint: str) -> PaymentRequestResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )


__all__ = ["FinanceService"]
