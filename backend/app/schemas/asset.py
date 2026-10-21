import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AssetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _clean_text(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


def _validate_metadata(value: object) -> object:
    if not isinstance(value, dict):
        raise ValueError("Metadata must be a JSON object.")
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("Metadata must contain valid JSON values.") from exc
    if len(encoded.encode("utf-8")) > 8192:
        raise ValueError("Metadata cannot exceed 8 KB.")
    return value


class ProductCreate(AssetRequest):
    organization_id: UUID
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    category: str = Field(min_length=1, max_length=80)
    quantity: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=3)
    unit: str | None = Field(default=None, max_length=24)

    @field_validator("sku", "name", "description", "category", "unit", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return _clean_text(value)


class ProductResponse(BaseModel):
    id: UUID
    organization_id: UUID
    sku: str
    name: str
    description: str | None
    category: str
    quantity: Decimal | None
    unit: str | None
    status: Literal["active", "discontinued"]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductPage(BaseModel):
    items: list[ProductResponse]
    limit: int
    offset: int
    has_more: bool


class AssetCreate(AssetRequest):
    organization_id: UUID
    product_id: UUID | None = None
    asset_identifier: str = Field(min_length=1, max_length=96)
    category: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    metadata: dict[str, object] = Field(default_factory=dict)

    @field_validator("asset_identifier", "category", "name", "description", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return _clean_text(value)

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, object]) -> dict[str, object]:
        return _validate_metadata(value)  # type: ignore[return-value]


class AssetResponse(BaseModel):
    id: UUID
    organization_id: UUID
    product_id: UUID | None
    asset_identifier: str
    category: str
    name: str
    description: str | None
    metadata: dict[str, object]
    current_owner_organization_id: UUID
    current_custodian_organization_id: UUID | None
    status: Literal["active", "retired"]
    created_at: datetime
    updated_at: datetime


class AssetPage(BaseModel):
    items: list[AssetResponse]
    limit: int
    offset: int
    has_more: bool


class AssetTransfer(AssetRequest):
    recipient_account_number: str = Field(min_length=9, max_length=18)

    @field_validator("recipient_account_number", mode="before")
    @classmethod
    def normalize_account_number(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = "".join(value.split())
        if re.fullmatch(r"\d{9,18}", normalized) is None:
            raise ValueError("Enter a valid LedgerChain account number.")
        return normalized


class CustodyChange(AssetRequest):
    custodian_account_number: str = Field(min_length=9, max_length=18)

    @field_validator("custodian_account_number", mode="before")
    @classmethod
    def normalize_account_number(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = "".join(value.split())
        if re.fullmatch(r"\d{9,18}", normalized) is None:
            raise ValueError("Enter a valid LedgerChain account number.")
        return normalized


class AssetStatusChange(AssetRequest):
    status: Literal["retired"]


class AssetEventResponse(BaseModel):
    id: UUID
    asset_id: UUID
    sequence_number: int
    event_type: str
    actor_user_id: UUID
    actor_organization_id: UUID
    previous_state: dict[str, object] | None
    resulting_state: dict[str, object]
    metadata: dict[str, object]
    created_at: datetime


class AssetHistoryResponse(BaseModel):
    asset_id: UUID
    items: list[AssetEventResponse]
    limit: int
    offset: int
    has_more: bool


class AssetOwnershipResponse(BaseModel):
    id: UUID
    asset_id: UUID
    organization_id: UUID
    event_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssetOwnershipPage(BaseModel):
    items: list[AssetOwnershipResponse]
    limit: int
    offset: int
    has_more: bool


class AssetVerificationResponse(BaseModel):
    asset_id: UUID
    exists: Literal[True]
    current_owner_organization_id: UUID
    current_custodian_organization_id: UUID | None
    status: str
    history_consistent: bool
    event_count: int
    latest_anchor_record_event_id: UUID | None
    blockchain_status: Literal["NOT_ANCHORED", "SIMULATED", "CONFIRMATION_PENDING", "ANCHORED_MATCH", "ANCHORED_MISMATCH"]
    integrity_warning: bool


__all__ = [
    "AssetCreate", "AssetEventResponse", "AssetHistoryResponse", "AssetOwnershipPage", "AssetOwnershipResponse", "AssetPage",
    "AssetResponse", "AssetStatusChange", "AssetTransfer", "AssetVerificationResponse", "CustodyChange",
    "ProductCreate", "ProductPage", "ProductResponse",
]


