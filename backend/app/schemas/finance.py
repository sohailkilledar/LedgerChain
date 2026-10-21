from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.payment import PaymentPurpose

MAX_AMOUNT = Decimal("9999999999999999.99")
RequestStatus = Literal["DRAFT", "SUBMITTED", "APPROVED", "REJECTED", "PAYMENT_CREATED", "COMPLETED"]


def _exact_amount(value: object) -> object:
    if not isinstance(value, (str, Decimal)):
        raise ValueError("Amount must be a decimal string with up to two fractional digits.")
    if isinstance(value, str) and re.fullmatch(r"\d+(?:\.\d{1,2})?", value) is None:
        raise ValueError("Amount must be a decimal string with up to two fractional digits.")
    try:
        amount = value if isinstance(value, Decimal) else Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("Enter a valid amount.") from exc
    if not amount.is_finite() or amount.as_tuple().exponent < -2 or amount <= 0 or amount > MAX_AMOUNT:
        raise ValueError("Enter a positive INR amount with up to two decimal places.")
    return amount


class BudgetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: UUID
    name: str = Field(min_length=1, max_length=120)
    category: str | None = Field(default=None, max_length=80)
    period_start: date
    period_end: date
    allocated_amount: Decimal

    @field_validator("name", "category", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("allocated_amount", mode="before")
    @classmethod
    def exact_amount(cls, value: object) -> object:
        return _exact_amount(value)

    @model_validator(mode="after")
    def valid_period(self) -> "BudgetCreate":
        if self.period_end < self.period_start:
            raise ValueError("The budget end date must be on or after its start date.")
        if not self.name:
            raise ValueError("A budget name is required.")
        return self


class PaymentRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: UUID
    recipient_account: str = Field(min_length=9, max_length=18)
    amount: Decimal
    purpose: PaymentPurpose
    note: str | None = Field(default=None, max_length=140)
    category: str | None = Field(default=None, max_length=80)
    budget_id: UUID | None = None

    @field_validator("recipient_account", mode="before")
    @classmethod
    def normalize_account(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = "".join(value.split())
        if re.fullmatch(r"\d{9,18}", normalized) is None:
            raise ValueError("Enter a valid LedgerChain account number.")
        return normalized

    @field_validator("amount", mode="before")
    @classmethod
    def exact_amount(cls, value: object) -> object:
        return _exact_amount(value)

    @field_validator("note", "category", mode="before")
    @classmethod
    def normalize_note_and_category(cls, value: object) -> object:
        return value.strip() or None if isinstance(value, str) else value


class BudgetResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    category: str | None
    period_start: date
    period_end: date
    allocated_amount: Decimal
    spent_amount: Decimal
    committed_amount: Decimal
    remaining_amount: Decimal
    utilization_percent: Decimal
    currency: Literal["INR"]
    status: Literal["active", "closed"]
    created_at: datetime


class FinanceBudgetPage(BaseModel):
    items: list[BudgetResponse]
    limit: int
    offset: int
    has_more: bool


class PaymentRequestResponse(BaseModel):
    id: UUID
    organization_id: UUID
    requester_user_id: UUID
    recipient_organization_id: UUID
    recipient_account: str
    recipient_name: str
    budget_id: UUID | None
    category: str | None
    amount: Decimal
    currency: Literal["INR"]
    purpose: PaymentPurpose
    note: str | None
    status: RequestStatus
    approver_user_id: UUID | None
    approval_note: str | None
    approved_at: datetime | None
    payment_id: UUID | None
    payment_reference: str | None
    created_at: datetime
    submitted_at: datetime | None
    completed_at: datetime | None


class PaymentRequestPage(BaseModel):
    items: list[PaymentRequestResponse]
    limit: int
    offset: int
    has_more: bool


class PaymentRequestDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str | None = Field(default=None, max_length=240)

    @field_validator("note", mode="before")
    @classmethod
    def normalize_note(cls, value: object) -> object:
        return value.strip() or None if isinstance(value, str) else value


class PaymentRequestEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_request_id: UUID
    sequence_number: int
    actor_user_id: UUID
    from_status: RequestStatus | None
    to_status: RequestStatus
    detail: str | None
    created_at: datetime


class PaymentRequestHistory(BaseModel):
    payment_request_id: UUID
    items: list[PaymentRequestEventResponse]


__all__ = [
    "BudgetCreate", "BudgetResponse", "FinanceBudgetPage", "PaymentRequestCreate", "PaymentRequestDecision",
    "PaymentRequestEventResponse", "PaymentRequestHistory", "PaymentRequestPage", "PaymentRequestResponse",
    "RequestStatus",
]
