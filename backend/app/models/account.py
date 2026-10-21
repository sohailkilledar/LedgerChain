from datetime import datetime
from decimal import Decimal
import secrets
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def generate_account_number() -> str:
    return str(secrets.randbelow(9 * 10**17) + 10**17)


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "account_type IN ('business', 'sole_proprietorship', 'partnership', 'corporation', 'nonprofit')",
            name="account_type",
        ),
        CheckConstraint("status IN ('active', 'suspended')", name="status"),
        CheckConstraint("length(account_number) = 18", name="account_number_length"),
        CheckConstraint("balance >= 0", name="balance_non_negative"),
        Index("ix_organizations_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    account_number: Mapped[str] = mapped_column(String(18), nullable=False, unique=True, default=generate_account_number)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    account_type: Mapped[str] = mapped_column(String(32), nullable=False, default="business", server_default="business")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        CheckConstraint("role IN ('owner', 'member')", name="role"),
        UniqueConstraint("organization_id", "user_id", name="organization_user"),
        Index("ix_organization_memberships_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="member", server_default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserSettings(Base):
    __tablename__ = "user_settings"
    __table_args__ = (
        CheckConstraint("date_format IN ('dmy', 'mdy', 'iso')", name="date_format"),
        Index("ix_user_settings_user_id", "user_id", unique=True),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    time_zone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC", server_default="UTC")
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="en", server_default="en")
    date_format: Mapped[str] = mapped_column(String(8), nullable=False, default="dmy", server_default="dmy")
    show_technical_by_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    share_usage_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class NotificationPreferences(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (Index("ix_notification_preferences_user_id", "user_id", unique=True),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    security_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    transaction_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    account_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    marketing_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


__all__ = ["NotificationPreferences", "Organization", "OrganizationMembership", "UserSettings"]

