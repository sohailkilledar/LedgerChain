from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, JSON, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'discontinued')", name="status"),
        CheckConstraint("quantity IS NULL OR quantity >= 0", name="quantity_non_negative"),
        UniqueConstraint("organization_id", "sku", name="uq_products_organization_sku"),
        Index("ix_products_organization_created", "organization_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 3))
    unit: Mapped[str | None] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'retired')", name="status"),
        UniqueConstraint("organization_id", "asset_identifier", name="uq_assets_organization_identifier"),
        Index("ix_assets_owner_created", "current_owner_organization_id", "created_at"),
        Index("ix_assets_custodian", "current_custodian_organization_id"),
        Index("ix_assets_product_id", "product_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"))
    asset_identifier: Mapped[str] = mapped_column(String(96), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    metadata_json: Mapped[dict[str, object]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    current_owner_organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    current_custodian_organization_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AssetEvent(Base):
    __tablename__ = "asset_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('REGISTERED', 'TRANSFERRED', 'CUSTODY_CHANGED', 'RETIRED', 'PROVENANCE_RECORDED')",
            name="event_type",
        ),
        CheckConstraint("sequence_number > 0", name="sequence_positive"),
        UniqueConstraint("asset_id", "sequence_number", name="uq_asset_events_asset_sequence"),
        UniqueConstraint("asset_id", "actor_organization_id", "idempotency_key", name="uq_asset_events_idempotency"),
        Index("ix_asset_events_asset_sequence", "asset_id", "sequence_number"),
        Index("ix_asset_events_actor_created", "actor_organization_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False)
    sequence_number: Mapped[int] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    actor_organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    previous_state: Mapped[dict[str, object] | None] = mapped_column(JSON)
    resulting_state: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AssetOwnership(Base):
    __tablename__ = "asset_ownerships"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_asset_ownerships_event"),
        Index("ix_asset_ownerships_asset_created", "asset_id", "created_at"),
        Index("ix_asset_ownerships_organization", "organization_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("asset_events.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


__all__ = ["Asset", "AssetEvent", "AssetOwnership", "Product"]


