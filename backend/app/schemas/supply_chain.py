from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.blockchain import BlockchainRecordResponse


ShipmentStatus = Literal["PREPARED", "DISPATCHED", "IN_TRANSIT", "RECEIVED", "REJECTED"]


class InventoryBatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: UUID
    product_id: UUID
    batch_code: str = Field(min_length=1, max_length=80)
    manufactured_on: date | None = None
    expires_on: date | None = None
    notes: str | None = Field(default=None, max_length=240)

    @field_validator("batch_code", "notes", mode="before")
    @classmethod
    def clean_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_dates(self) -> "InventoryBatchCreate":
        if self.manufactured_on and self.expires_on and self.manufactured_on > self.expires_on:
            raise ValueError("Manufacture date cannot be after the expiry date.")
        return self


class InventoryBatchResponse(BaseModel):
    id: UUID
    organization_id: UUID
    product_id: UUID
    sku: str
    product_name: str
    unit: str | None
    batch_code: str
    manufactured_on: date | None
    expires_on: date | None
    notes: str | None
    created_by_user_id: UUID
    created_at: datetime


class InventoryShipmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: UUID
    recipient_account_number: str = Field(min_length=18, max_length=18)
    product_id: UUID
    batch_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=3)
    source_location: str = Field(min_length=1, max_length=120)
    destination_location: str = Field(min_length=1, max_length=120)
    note: str | None = Field(default=None, max_length=240)

    @field_validator("recipient_account_number", "source_location", "destination_location", "note", mode="before")
    @classmethod
    def clean_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class InventoryShipmentEventResponse(BaseModel):
    id: UUID
    sequence_number: int
    actor_user_id: UUID
    actor_organization_id: UUID
    from_status: ShipmentStatus | None
    to_status: ShipmentStatus
    detail: str | None
    created_at: datetime
    blockchain_record: BlockchainRecordResponse | None = None


class InventoryShipmentResponse(BaseModel):
    id: UUID
    sender_organization_id: UUID
    sender_name: str
    sender_account_number: str
    recipient_organization_id: UUID
    recipient_name: str
    recipient_account_number: str
    product_id: UUID
    product_name: str
    sku: str
    unit: str | None
    batch_id: UUID
    batch_code: str
    quantity: Decimal
    source_location: str
    destination_location: str
    status: ShipmentStatus
    note: str | None
    rejection_reason: str | None
    created_by_user_id: UUID
    dispatcher_user_id: UUID | None
    receiver_user_id: UUID | None
    created_at: datetime
    dispatched_at: datetime | None
    in_transit_at: datetime | None
    received_at: datetime | None
    rejected_at: datetime | None
    events: list[InventoryShipmentEventResponse]


class InventoryShipmentPage(BaseModel):
    items: list[InventoryShipmentResponse]
    limit: int
    offset: int
    has_more: bool


class InventoryShipmentReceive(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination_location: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("destination_location", mode="before")
    @classmethod
    def clean_destination(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class InventoryShipmentReject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=240)

    @field_validator("reason", mode="before")
    @classmethod
    def clean_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value
