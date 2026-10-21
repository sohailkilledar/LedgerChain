from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.inventory import InventoryActivityResponse


class FinanceActivityResponse(BaseModel):
    id: UUID
    type: Literal["finance"] = "finance"
    finance_record_type: Literal["payment_request", "budget"] = "payment_request"
    status: Literal["completed", "pending", "failed"]
    title: str
    summary: str
    timestamp: datetime
    reference: str
    payment_request_id: UUID | None = None
    payment_id: UUID | None = None
    budget_id: UUID | None = None
    budget_name: str | None = None
    budget_category: str | None = None
    budget_period_start: date | None = None
    budget_period_end: date | None = None
    request_status: str | None = None
    event_status: str
    sequence_number: int
    recipient_name: str | None = None
    recipient_account: str | None = None
    amount: Decimal
    currency: Literal["INR"]
    actor_user_id: UUID
    actor_organization_id: UUID
    detail: str | None = None


class ShipmentActivityResponse(BaseModel):
    id: UUID
    type: Literal["shipment"] = "shipment"
    status: Literal["completed", "pending", "failed"]
    title: str
    summary: str
    timestamp: datetime
    reference: str
    shipment_id: UUID
    shipment_status: str
    event_status: str
    sequence_number: int
    actor_user_id: UUID
    actor_organization_id: UUID
    sender_organization_id: UUID
    sender_name: str
    sender_account_number: str
    recipient_organization_id: UUID
    recipient_name: str
    recipient_account_number: str
    product_id: UUID
    product_name: str
    sku: str
    batch_id: UUID
    batch_code: str
    quantity: Decimal
    unit: str | None
    source_location: str
    destination_location: str
    detail: str | None


class ActivityResponse(BaseModel):
    id: UUID
    type: Literal["payment"]
    status: Literal["completed"]
    title: str
    summary: str
    direction: Literal["incoming", "outgoing"]
    amount: Decimal
    currency: Literal["INR"]
    counterparty: str
    counterparty_account: str
    timestamp: datetime
    reference: str
    payment_id: UUID
    ledger_transaction_id: UUID


class AssetActivityResponse(BaseModel):
    id: UUID
    type: Literal["asset"] = "asset"
    status: Literal["completed"] = "completed"
    title: str
    summary: str
    timestamp: datetime
    reference: str
    asset_id: UUID
    asset_name: str
    asset_identifier: str
    event_type: str
    sequence_number: int
    actor_user_id: UUID
    actor_organization_id: UUID
    previous_state: dict[str, object] | None
    resulting_state: dict[str, object]
    metadata: dict[str, object]


class BlockchainActivityResponse(BaseModel):
    id: UUID
    type: Literal["blockchain"] = "blockchain"
    status: Literal["completed", "pending", "failed"]
    title: str
    summary: str
    timestamp: datetime
    reference: str
    anchor_status: Literal["submitting", "submitted", "confirmed", "failed", "submission_failed", "simulated"]
    provider: str
    network: str
    digest: str
    digest_version: str
    asset_event_id: UUID | None
    shipment_event_id: UUID | None
    ledger_transaction_id: UUID | None
    transaction_hash: str | None
    block_number: int | None
    confirmed_at: datetime | None


ActivityItem = ActivityResponse | FinanceActivityResponse | ShipmentActivityResponse | AssetActivityResponse | InventoryActivityResponse | BlockchainActivityResponse


class ActivityPage(BaseModel):
    items: list[ActivityItem]
    limit: int
    offset: int
    has_more: bool


class LedgerEntryResponse(BaseModel):
    id: UUID
    account_id: UUID
    direction: Literal["debit", "credit"]
    amount: Decimal
    currency: Literal["INR"]
    timestamp: datetime
    description: str | None


class LedgerTransactionResponse(BaseModel):
    id: UUID
    payment_id: UUID
    reference: str
    transaction_type: Literal["payment_transfer"]
    status: Literal["posted"]
    amount: Decimal
    currency: Literal["INR"]
    created_at: datetime
    posted_at: datetime
    entries: list[LedgerEntryResponse]


__all__ = [
    "ActivityPage",
    "ActivityResponse",
    "LedgerEntryResponse",
    "LedgerTransactionResponse",
]
