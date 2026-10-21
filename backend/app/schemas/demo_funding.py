import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.schemas.account import AccountRequest

MAX_DEMO_FUNDING = Decimal("1000000.00")


class DemoFundingCreate(AccountRequest):
    amount: Decimal

    @field_validator("amount", mode="before")
    @classmethod
    def parse_demo_amount(cls, value: object) -> object:
        if not isinstance(value, str) or re.fullmatch(r"\d+(?:\.\d{1,2})?", value) is None:
            raise ValueError("Enter an amount with up to two decimal places.")
        try:
            amount = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("Enter a valid amount.") from exc
        if not amount.is_finite() or amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        if amount > MAX_DEMO_FUNDING:
            raise ValueError("Demo funding is limited to ₹10,00,000 per request.")
        return amount.quantize(Decimal("0.01"))


class DemoFundingResponse(BaseModel):
    id: UUID
    reference: str
    amount: Decimal
    balance: Decimal
    currency: Literal["INR"]
    demo: Literal[True] = True
    created_at: datetime


__all__ = ["DemoFundingCreate", "DemoFundingResponse", "MAX_DEMO_FUNDING"]

