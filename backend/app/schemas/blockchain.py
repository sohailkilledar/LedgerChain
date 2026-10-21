from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

BlockchainStatus = Literal["submitting", "submitted", "confirmed", "failed", "submission_failed", "simulated"]
VerificationStatus = Literal["ANCHORED_MATCH", "ANCHORED_MISMATCH", "NOT_ANCHORED", "CONFIRMATION_PENDING"]


class BlockchainRecordResponse(BaseModel):
    id: UUID
    ledger_transaction_id: UUID | None
    asset_event_id: UUID | None = None
    shipment_event_id: UUID | None = None
    provider: str
    network: str
    chain_id: int | None
    contract_address: str | None
    contract_version: str | None
    digest_version: str
    digest: str
    status: BlockchainStatus
    transaction_hash: str | None
    block_number: int | None
    submitted_at: datetime | None
    confirmed_at: datetime | None
    failure_code: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BlockchainStatusResponse(BaseModel):
    enabled: bool
    provider: str
    network: str
    chain_id: int | None
    contract_address: str | None
    contract_version: str | None
    health: Literal["available", "simulated", "unavailable", "disabled"]


class ShipmentEventVerificationResponse(BaseModel):
    shipment_id: UUID
    shipment_event_id: UUID
    exists: Literal[True]
    history_consistent: bool
    event_count: int
    blockchain_status: Literal["NOT_ANCHORED", "SIMULATED", "CONFIRMATION_PENDING", "VERIFICATION_UNAVAILABLE", "ANCHORED_MATCH", "ANCHORED_MISMATCH"]
    integrity_warning: bool
    anchor_record: BlockchainRecordResponse | None


class BlockchainVerificationResponse(BaseModel):
    ledger_transaction_id: UUID
    result: VerificationStatus
    digest_version: str
    current_digest: str
    anchored_digest: str | None
    anchor_timestamp: datetime | None
    transaction_hash: str | None
    block_number: int | None
    contract_address: str | None
    integrity_warning: bool


__all__ = [
    "BlockchainRecordResponse",
    "BlockchainStatusResponse",
    "BlockchainStatus",
    "BlockchainVerificationResponse",
    "ShipmentEventVerificationResponse",
    "VerificationStatus",
]
