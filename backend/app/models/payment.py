from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("fee >= 0", name="fee_non_negative"),
        CheckConstraint("total_debit = amount + fee", name="total_debit_matches"),
        CheckConstraint("currency = 'INR'", name="currency"),
        CheckConstraint("purpose IN ('invoice', 'supplier', 'salary', 'personal', 'other')", name="purpose"),
        CheckConstraint("status IN ('pending', 'processing', 'completed')", name="status"),
        Index("ix_payments_sender_created", "sender_organization_id", "created_at"),
        Index("ix_payments_recipient_created", "recipient_organization_id", "created_at"),
        Index("ix_payments_status_created", "status", "created_at"),
        UniqueConstraint("sender_organization_id", "idempotency_key", name="uq_payments_sender_idempotency"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    reference: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    sender_organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    sender_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    recipient_organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    sender_account_number: Mapped[str] = mapped_column(String(18), nullable=False)
    recipient_account_number: Mapped[str] = mapped_column(String(18), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(160), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    total_debit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR", server_default="INR")
    purpose: Mapped[str] = mapped_column(String(24), nullable=False)
    note: Mapped[str | None] = mapped_column(String(140))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", server_default="pending")
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


__all__ = ["Payment"]
