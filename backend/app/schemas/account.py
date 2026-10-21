import re
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

AccountType = Literal["business", "sole_proprietorship", "partnership", "corporation", "nonprofit"]
DateFormat = Literal["dmy", "mdy", "iso"]


class AccountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserProfileResponse(BaseModel):
    id: UUID
    email: str
    display_name: str | None
    phone: str | None
    account_status: str
    email_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(AccountRequest):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("display_name", "phone", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("display_name")
    @classmethod
    def reject_blank_display_name(cls, value: str | None) -> str | None:
        if value == "":
            raise ValueError("Display name cannot be blank.")
        return value


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    account_number: str
    balance: Decimal
    account_type: AccountType
    status: str
    role: Literal["owner", "member"]
    created_at: datetime
    updated_at: datetime


class OrganizationUpdate(AccountRequest):
    name: str = Field(default=None, min_length=1, max_length=160)
    account_type: AccountType = None

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("account_type")
    @classmethod
    def require_account_type(cls, value: AccountType) -> AccountType:
        if value is None:
            raise ValueError("Account type cannot be null.")
        return value

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        if not value:
            raise ValueError("Organization name cannot be blank.")
        return value


class UserSettingsResponse(BaseModel):
    user_id: UUID
    time_zone: str
    locale: str
    date_format: DateFormat
    show_technical_by_default: bool
    share_usage_data: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserSettingsUpdate(AccountRequest):
    time_zone: str = Field(default=None, min_length=1, max_length=64)
    locale: str = Field(default=None, min_length=2, max_length=16)
    date_format: DateFormat = None
    show_technical_by_default: bool = None
    share_usage_data: bool = None

    @field_validator("time_zone")
    @classmethod
    def validate_time_zone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except (ValueError, ZoneInfoNotFoundError) as exc:
                raise ValueError("Enter a valid IANA time zone.") from exc
        return value

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(r"[a-z]{2}(?:-[A-Z]{2})?", value) is None:
            raise ValueError("Enter a locale such as en or en-IN.")
        return value


class NotificationPreferencesResponse(BaseModel):
    user_id: UUID
    security_notifications: bool
    transaction_notifications: bool
    account_notifications: bool
    marketing_notifications: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferencesUpdate(AccountRequest):
    security_notifications: bool = None
    transaction_notifications: bool = None
    account_notifications: bool = None
    marketing_notifications: bool = None


__all__ = [
    "AccountType",
    "NotificationPreferencesResponse",
    "NotificationPreferencesUpdate",
    "OrganizationResponse",
    "OrganizationUpdate",
    "UserProfileResponse",
    "UserProfileUpdate",
    "UserSettingsResponse",
    "UserSettingsUpdate",
]
