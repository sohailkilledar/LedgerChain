from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InventoryStock(Base):
    __tablename__ = "inventory_stocks"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
        CheckConstraint("low_stock_threshold IS NULL OR low_stock_threshold >= 0", name="threshold_non_negative"),
        Index("uq_inventory_stocks_unbatched_location", "organization_id", "product_id", "location", unique=True, sqlite_where=__import__("sqlalchemy").text("batch_id IS NULL"), postgresql_where=__import__("sqlalchemy").text("batch_id IS NULL")),
        Index("uq_inventory_stocks_batched_location", "organization_id", "product_id", "location", "batch_id", unique=True, sqlite_where=__import__("sqlalchemy").text("batch_id IS NOT NULL"), postgresql_where=__import__("sqlalchemy").text("batch_id IS NOT NULL")),
        Index("ix_inventory_stocks_organization_updated", "organization_id", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    batch_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("inventory_batches.id", ondelete="RESTRICT"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False, default=Decimal("0"), server_default="0")
    low_stock_threshold: Mapped[Decimal | None] = mapped_column(Numeric(18, 3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint("movement_type IN ('stock_in', 'stock_out', 'movement', 'adjustment')", name="movement_type"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("adjustment_delta IS NULL OR adjustment_delta != 0", name="adjustment_delta_nonzero"),
        CheckConstraint("source_location IS NOT NULL OR destination_location IS NOT NULL", name="location_required"),
        CheckConstraint("source_quantity_before IS NULL OR source_quantity_before >= 0", name="source_before_non_negative"),
        CheckConstraint("source_quantity_after IS NULL OR source_quantity_after >= 0", name="source_after_non_negative"),
        CheckConstraint("destination_quantity_before IS NULL OR destination_quantity_before >= 0", name="destination_before_non_negative"),
        CheckConstraint("destination_quantity_after IS NULL OR destination_quantity_after >= 0", name="destination_after_non_negative"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_inventory_movement_idempotency"),
        Index("ix_inventory_movements_organization_created", "organization_id", "created_at"),
        Index("ix_inventory_movements_product_created", "product_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    actor_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_location: Mapped[str | None] = mapped_column(String(120))
    destination_location: Mapped[str | None] = mapped_column(String(120))
    batch_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("inventory_batches.id", ondelete="RESTRICT"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    adjustment_delta: Mapped[Decimal | None] = mapped_column(Numeric(18, 3))
    reason: Mapped[str | None] = mapped_column(String(240))
    source_quantity_before: Mapped[Decimal | None] = mapped_column(Numeric(18, 3))
    source_quantity_after: Mapped[Decimal | None] = mapped_column(Numeric(18, 3))
    destination_quantity_before: Mapped[Decimal | None] = mapped_column(Numeric(18, 3))
    destination_quantity_after: Mapped[Decimal | None] = mapped_column(Numeric(18, 3))
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


__all__ = ["InventoryMovement", "InventoryStock"]

