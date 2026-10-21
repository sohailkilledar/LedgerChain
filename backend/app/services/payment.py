from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import secrets
from typing import Literal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.auth import User
from app.models.payment import Payment
from app.repositories.payment import PaymentAccountRepository, PaymentRepository
from app.schemas.payment import PaymentCreate
from app.services.ledger import LedgerService

PAYMENT_FEE = Decimal("0.00")
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"processing"}),
    "processing": frozenset({"completed"}),
    "completed": frozenset(),
}


class PaymentService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.accounts = PaymentAccountRepository(session)
        self.payments = PaymentRepository(session)

    @staticmethod
    def transition(payment: Payment, target: Literal["pending", "processing", "completed"]) -> None:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def create(
        self,
        user: User,
        request: PaymentCreate,
        idempotency_key: str,
        *,
        sender_organization_id: UUID | None = None,
    ) -> Payment:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def get(self, payment_id: UUID, user: User) -> Payment:
        payment = self.payments.get(payment_id)
        if payment is None:
            raise NotFoundError("The payment was not found.", code="PAYMENT_NOT_FOUND")
        if payment.sender_user_id == user.id:
            return payment
        if self.accounts.user_is_member(user.id, payment.sender_organization_id):
            return payment
        if self.accounts.user_is_member(user.id, payment.recipient_organization_id):
            return payment
        raise NotFoundError("The payment was not found.", code="PAYMENT_NOT_FOUND")

    def list_for_user(self, user: User, *, limit: int, offset: int) -> tuple[list[Payment], bool]:
        organization_ids = self.accounts.organization_ids_for_user(user.id)
        rows = self.payments.list_for_user(user.id, organization_ids, limit=limit + 1, offset=offset)
        return rows[:limit], len(rows) > limit

    @staticmethod
    def _fingerprint(request: PaymentCreate) -> str:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    @staticmethod
    def _replay_or_conflict(existing: Payment, fingerprint: str) -> Payment:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )


__all__ = ["PAYMENT_FEE", "PaymentService"]
