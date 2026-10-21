from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"
    __table_args__ = (
        CheckConstraint("transaction_type IN ('payment_transfer')", name="transaction_type"),
        CheckConstraint("status IN ('draft', 'posted')", name="status"),
        CheckConstraint("status != 'posted' OR posted_at IS NOT NULL", name="posted_timestamp"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("currency = 'INR'", name="currency"),
        Index("ix_ledger_transactions_created_at", "created_at"),
        UniqueConstraint("payment_id", name="uq_ledger_transactions_payment_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    payment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False
    )
    reference: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", server_default="draft")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR", server_default="INR")
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("direction IN ('debit', 'credit')", name="direction"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("currency = 'INR'", name="currency"),
        Index("ix_ledger_entries_account_created", "account_id", "created_at"),
        Index("ix_ledger_entries_transaction_id", "ledger_transaction_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    ledger_transaction_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ledger_transactions.id", ondelete="RESTRICT"), nullable=False
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR", server_default="INR")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    description: Mapped[str | None] = mapped_column(String(160))


__all__ = ["LedgerEntry", "LedgerTransaction"]
