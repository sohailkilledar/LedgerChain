from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BlockchainRecord(Base):
    __tablename__ = "blockchain_records"
    __table_args__ = (
        CheckConstraint(
            "status IN ('submitting', 'submitted', 'confirmed', 'failed', 'submission_failed', 'simulated')",
            name="status",
        ),
        CheckConstraint("length(digest) = 64", name="digest_length"),
        CheckConstraint("chain_id IS NULL OR chain_id > 0", name="chain_id_positive"),
        CheckConstraint(
            "status NOT IN ('submitted', 'confirmed') OR (transaction_hash IS NOT NULL AND submitted_at IS NOT NULL)",
            name="submitted_fields",
        ),
        CheckConstraint("status != 'confirmed' OR confirmed_at IS NOT NULL", name="confirmed_timestamp"),
        CheckConstraint("status NOT IN ('submission_failed', 'failed') OR failure_code IS NOT NULL", name="failure_code_required"),
        CheckConstraint(
            "status != 'failed' OR (transaction_hash IS NOT NULL AND confirmed_at IS NOT NULL)",
            name="failed_transaction_fields",
        ),
        CheckConstraint(
            "status != 'simulated' OR (transaction_hash IS NULL AND block_number IS NULL AND submitted_at IS NULL AND confirmed_at IS NULL)",
            name="simulated_without_chain_data",
        ),
        CheckConstraint("block_number IS NULL OR block_number >= 0", name="block_number_non_negative"),
        CheckConstraint(
            "(ledger_transaction_id IS NOT NULL AND asset_event_id IS NULL AND shipment_event_id IS NULL) OR "
            "(ledger_transaction_id IS NULL AND asset_event_id IS NOT NULL AND shipment_event_id IS NULL) OR "
            "(ledger_transaction_id IS NULL AND asset_event_id IS NULL AND shipment_event_id IS NOT NULL)",
            name="record_reference",
        ),
        UniqueConstraint("ledger_transaction_id", name="ledger_transaction_id"),
        UniqueConstraint("asset_event_id", name="asset_event_id"),
        UniqueConstraint("shipment_event_id", name="shipment_event_id"),
        UniqueConstraint("provider", "network", "transaction_hash", name="provider_network_transaction_hash"),
        Index("ix_blockchain_records_status_created", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    ledger_transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ledger_transactions.id", ondelete="RESTRICT")
    )
    asset_event_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("asset_events.id", ondelete="RESTRICT")
    )
    shipment_event_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("inventory_shipment_events.id", ondelete="RESTRICT")
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    network: Mapped[str] = mapped_column(String(64), nullable=False)
    chain_id: Mapped[int | None] = mapped_column(Integer)
    contract_address: Mapped[str | None] = mapped_column(String(42))
    contract_version: Mapped[str | None] = mapped_column(String(24))
    digest_version: Mapped[str] = mapped_column(String(32), nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="submitting")
    transaction_hash: Mapped[str | None] = mapped_column(String(256))
    block_number: Mapped[int | None] = mapped_column(Integer)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


__all__ = ["BlockchainRecord"]
