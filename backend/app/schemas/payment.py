import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.account import AccountRequest

PaymentPurpose = Literal["invoice", "supplier", "salary", "personal", "other"]
PaymentStatus = Literal["pending", "processing", "completed"]
MAX_AMOUNT = Decimal("9999999999999999.99")


class PaymentCreate(AccountRequest):
    recipient_account: str = Field(min_length=9, max_length=18)
    amount: Decimal
    currency: Literal["INR"] = "INR"
    purpose: PaymentPurpose
    note: str | None = Field(default=None, max_length=140)

    @field_validator("recipient_account", mode="before")
    @classmethod
    def normalize_account_number(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = "".join(value.split())
        if re.fullmatch(r"\d{9,18}", normalized) is None:
            raise ValueError("Enter a valid LedgerChain account number.")
        return normalized

    @field_validator("amount", mode="before")
    @classmethod
    def parse_exact_amount(cls, value: object) -> object:
        if not isinstance(value, (str, Decimal)):
            raise ValueError("Amount must be a decimal string with up to two fractional digits.")
        if isinstance(value, str) and re.fullmatch(r"\d+(?:\.\d{1,2})?", value) is None:
            raise ValueError("Amount must be a decimal string with up to two fractional digits.")
        try:
            amount = value if isinstance(value, Decimal) else Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("Enter a valid amount.") from exc
        if not amount.is_finite() or amount.as_tuple().exponent < -2:
            raise ValueError("Amount supports at most two fractional digits.")
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        if amount > MAX_AMOUNT:
            raise ValueError("Amount exceeds the supported limit.")
        return amount

    @field_validator("note", mode="before")
    @classmethod
    def normalize_note(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class PaymentResponse(BaseModel):
    id: UUID
    reference: str
    sender_organization_id: UUID
    recipient_organization_id: UUID
    sender_account: str
    recipient_account: str
    recipient_name: str
    amount: Decimal
    fee: Decimal
    total_debit: Decimal
    currency: Literal["INR"]
    purpose: PaymentPurpose
    note: str | None
    status: PaymentStatus
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class PaymentPage(BaseModel):
    items: list[PaymentResponse]
    limit: int
    offset: int
    has_more: bool


__all__ = ["PaymentCreate", "PaymentPage", "PaymentPurpose", "PaymentResponse", "PaymentStatus"]
