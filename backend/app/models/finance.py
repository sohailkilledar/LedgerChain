from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


REQUEST_STATES = "'DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED', 'PAYMENT_CREATED', 'COMPLETED'"


class FinanceBudget(Base):
    __tablename__ = "finance_budgets"
    __table_args__ = (
        CheckConstraint("allocated_amount > 0", name="allocated_positive"),
        CheckConstraint("period_start <= period_end", name="period_order"),
        CheckConstraint("currency = 'INR'", name="currency"),
        CheckConstraint("status IN ('active', 'closed')", name="status"),
        Index("ix_finance_budgets_organization_period", "organization_id", "period_start", "period_end"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str | None] = mapped_column(String(80))
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR", server_default="INR")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", server_default="active")
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class PaymentRequest(Base):
    __tablename__ = "payment_requests"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("currency = 'INR'", name="currency"),
        CheckConstraint("purpose IN ('invoice', 'supplier', 'salary', 'personal', 'other')", name="purpose"),
        CheckConstraint(f"status IN ({REQUEST_STATES})", name="status"),
        Index("ix_payment_requests_organization_status_created", "organization_id", "status", "created_at"),
        Index("ix_payment_requests_budget_status", "budget_id", "status"),
        UniqueConstraint("organization_id", "requester_user_id", "idempotency_key", name="uq_payment_request_idempotency"),
        UniqueConstraint("payment_id", name="uq_payment_request_payment"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False)
    requester_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    recipient_organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False)
    recipient_account_number: Mapped[str] = mapped_column(String(18), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(160), nullable=False)
    budget_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("finance_budgets.id", ondelete="RESTRICT"))
    category: Mapped[str | None] = mapped_column(String(80))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR", server_default="INR")
    purpose: Mapped[str] = mapped_column(String(24), nullable=False)
    note: Mapped[str | None] = mapped_column(String(140))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT", server_default="DRAFT")
    approver_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    approval_note: Mapped[str | None] = mapped_column(String(240))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("payments.id", ondelete="RESTRICT"))
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PaymentRequestEvent(Base):
    __tablename__ = "payment_request_events"
    __table_args__ = (
        CheckConstraint(f"to_status IN ({REQUEST_STATES})", name="to_status"),
        CheckConstraint(f"from_status IS NULL OR from_status IN ({REQUEST_STATES})", name="from_status"),
        CheckConstraint("sequence_number > 0", name="sequence_positive"),
        UniqueConstraint("payment_request_id", "sequence_number", name="uq_payment_request_event_sequence"),
        Index("ix_payment_request_events_request_created", "payment_request_id", "sequence_number"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    payment_request_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("payment_requests.id", ondelete="RESTRICT"), nullable=False)
    sequence_number: Mapped[int] = mapped_column(nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(24))
    to_status: Mapped[str] = mapped_column(String(24), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(240))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


__all__ = ["FinanceBudget", "PaymentRequest", "PaymentRequestEvent", "REQUEST_STATES"]
