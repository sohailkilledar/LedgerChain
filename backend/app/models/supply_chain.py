from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InventoryBatch(Base):
    __tablename__ = "inventory_batches"
    __table_args__ = (
        UniqueConstraint("organization_id", "product_id", "batch_code", name="uq_inventory_batch_product_code"),
        CheckConstraint(
            "manufactured_on IS NULL OR expires_on IS NULL OR manufactured_on <= expires_on",
            name="batch_date_order",
        ),
        Index("ix_inventory_batches_organization_created", "organization_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False)
    product_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    batch_code: Mapped[str] = mapped_column(String(80), nullable=False)
    manufactured_on: Mapped[date | None] = mapped_column(Date)
    expires_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(String(240))
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class InventoryShipment(Base):
    __tablename__ = "inventory_shipments"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("status IN ('PREPARED', 'DISPATCHED', 'IN_TRANSIT', 'RECEIVED', 'REJECTED')", name="status"),
        CheckConstraint("sender_organization_id != recipient_organization_id", name="organizations_differ"),
        UniqueConstraint("sender_organization_id", "idempotency_key", name="uq_inventory_shipment_idempotency"),
        Index("ix_inventory_shipments_sender_status", "sender_organization_id", "status", "created_at"),
        Index("ix_inventory_shipments_recipient_status", "recipient_organization_id", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    sender_organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False)
    recipient_organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False)
    product_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    batch_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("inventory_batches.id", ondelete="RESTRICT"), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    dispatcher_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    receiver_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    source_location: Mapped[str] = mapped_column(String(120), nullable=False)
    destination_location: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PREPARED", server_default="PREPARED")
    note: Mapped[str | None] = mapped_column(String(240))
    rejection_reason: Mapped[str | None] = mapped_column(String(240))
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    in_transit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InventoryShipmentEvent(Base):
    __tablename__ = "inventory_shipment_events"
    __table_args__ = (
        CheckConstraint("sequence_number > 0", name="sequence_positive"),
        CheckConstraint("from_status IS NULL OR from_status IN ('PREPARED', 'DISPATCHED', 'IN_TRANSIT', 'RECEIVED', 'REJECTED')", name="from_status"),
        CheckConstraint("to_status IN ('PREPARED', 'DISPATCHED', 'IN_TRANSIT', 'RECEIVED', 'REJECTED')", name="to_status"),
        UniqueConstraint("shipment_id", "sequence_number", name="uq_inventory_shipment_event_sequence"),
        UniqueConstraint("shipment_id", "idempotency_key", name="uq_inventory_shipment_event_idempotency"),
        Index("ix_inventory_shipment_events_shipment_sequence", "shipment_id", "sequence_number"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    shipment_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("inventory_shipments.id", ondelete="RESTRICT"), nullable=False)
    sequence_number: Mapped[int] = mapped_column(nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    actor_organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(16))
    to_status: Mapped[str] = mapped_column(String(16), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(240))
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


__all__ = ["InventoryBatch", "InventoryShipment", "InventoryShipmentEvent"]
