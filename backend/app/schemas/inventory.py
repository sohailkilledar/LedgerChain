from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MovementType = Literal["stock_in", "stock_out", "movement", "adjustment"]


class InventoryMovementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: UUID
    product_id: UUID
    batch_id: UUID | None = None
    movement_type: MovementType
    quantity: Decimal = Field(ge=0, max_digits=18, decimal_places=3)
    source_location: str | None = Field(default=None, min_length=1, max_length=120)
    destination_location: str | None = Field(default=None, min_length=1, max_length=120)
    adjustment_delta: Decimal | None = Field(default=None, max_digits=18, decimal_places=3)
    reason: str | None = Field(default=None, max_length=240)
    low_stock_threshold: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=3)

    @field_validator("source_location", "destination_location", "reason", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_movement(self) -> "InventoryMovementCreate":
        if self.movement_type == "stock_in":
            if self.quantity <= 0 or not self.destination_location or self.source_location:
                raise ValueError("Stock-in requires a positive quantity and destination location only.")
            if self.adjustment_delta is not None:
                raise ValueError("Stock-in cannot include an adjustment delta.")
        elif self.movement_type == "stock_out":
            if self.quantity <= 0 or not self.source_location or self.destination_location:
                raise ValueError("Stock-out requires a positive quantity and source location only.")
            if self.adjustment_delta is not None:
                raise ValueError("Stock-out cannot include an adjustment delta.")
        elif self.movement_type == "movement":
            if self.quantity <= 0 or not self.source_location or not self.destination_location:
                raise ValueError("A stock movement requires a positive quantity, source, and destination.")
            if self.source_location.casefold() == self.destination_location.casefold():
                raise ValueError("Source and destination locations must be different.")
            if self.adjustment_delta is not None:
                raise ValueError("A stock movement cannot include an adjustment delta.")
        else:
            if not self.destination_location or self.source_location:
                raise ValueError("An adjustment requires its destination location only.")
            if self.adjustment_delta is None or self.adjustment_delta == 0:
                raise ValueError("An adjustment requires a non-zero signed adjustment delta.")
            if self.adjustment_delta > 0 and self.quantity != self.adjustment_delta:
                raise ValueError("The adjustment quantity must match its positive delta.")
            if self.adjustment_delta < 0 and self.quantity != abs(self.adjustment_delta):
                raise ValueError("The adjustment quantity must match the absolute delta.")
            if not self.reason:
                raise ValueError("A reason is required for inventory adjustments.")
        return self


class InventoryStockResponse(BaseModel):
    id: UUID
    organization_id: UUID
    product_id: UUID
    sku: str
    product_name: str
    unit: str | None
    batch_id: UUID | None
    batch_code: str | None
    location: str
    quantity: Decimal
    low_stock_threshold: Decimal | None
    is_low_stock: bool
    updated_at: datetime


class InventoryStockPage(BaseModel):
    items: list[InventoryStockResponse]
    limit: int
    offset: int
    has_more: bool


class InventoryMovementResponse(BaseModel):
    id: UUID
    organization_id: UUID
    product_id: UUID
    sku: str
    product_name: str
    unit: str | None
    batch_id: UUID | None
    batch_code: str | None
    actor_user_id: UUID
    movement_type: MovementType
    source_location: str | None
    destination_location: str | None
    quantity: Decimal
    adjustment_delta: Decimal | None
    reason: str | None
    source_quantity_before: Decimal | None
    source_quantity_after: Decimal | None
    destination_quantity_before: Decimal | None
    destination_quantity_after: Decimal | None
    created_at: datetime


class InventoryMovementPage(BaseModel):
    items: list[InventoryMovementResponse]
    limit: int
    offset: int
    has_more: bool


class InventoryActivityResponse(BaseModel):
    id: UUID
    type: Literal["inventory"] = "inventory"
    status: Literal["completed"] = "completed"
    title: str
    summary: str
    timestamp: datetime
    reference: str
    organization_id: UUID
    product_id: UUID
    sku: str
    product_name: str
    movement_type: MovementType
    quantity: Decimal
    unit: str | None
    source_location: str | None
    destination_location: str | None
    adjustment_delta: Decimal | None
    reason: str | None
    actor_user_id: UUID

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "InventoryActivityResponse", "InventoryMovementCreate", "InventoryMovementPage", "InventoryMovementResponse",
    "InventoryStockPage", "InventoryStockResponse", "MovementType",
]
