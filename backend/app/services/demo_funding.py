from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import secrets

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.auth import User
from app.models.demo_funding import DemoFunding
from app.repositories.demo_funding import DemoFundingRepository
from app.repositories.payment import PaymentAccountRepository
from app.schemas.demo_funding import DemoFundingCreate, DemoFundingResponse

MAX_ACCOUNT_BALANCE = Decimal("9999999999999999.99")


class DemoFundingService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.fundings = DemoFundingRepository(session)
        self.accounts = PaymentAccountRepository(session)

    def create(self, user: User, request: DemoFundingCreate, idempotency_key: str) -> DemoFundingResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    @staticmethod
    def _replay(funding: DemoFunding, fingerprint: str, balance: Decimal) -> DemoFundingResponse:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    @staticmethod
    def _response(funding: DemoFunding, balance: Decimal) -> DemoFundingResponse:
        return DemoFundingResponse(
            id=funding.id,
            reference=funding.reference,
            amount=funding.amount,
            balance=balance,
            currency="INR",
            demo=True,
            created_at=funding.created_at,
        )


__all__ = ["DemoFundingService"]

