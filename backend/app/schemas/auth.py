from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class AuthRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterRequest(AuthRequest):
    email: EmailStr
    password: str = Field(min_length=1, max_length=4096)
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    organization_name: str | None = Field(default=None, min_length=1, max_length=160)

    @field_validator("display_name", "organization_name", mode="before")
    @classmethod
    def strip_registration_names(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("display_name", "organization_name")
    @classmethod
    def reject_blank_registration_names(cls, value: str | None) -> str | None:
        if value == "":
            raise ValueError("This field cannot be blank.")
        return value


class LoginRequest(AuthRequest):
    email: EmailStr
    password: str = Field(min_length=1, max_length=4096)
    remember: bool = True


class EmailRequest(AuthRequest):
    email: EmailStr


class TokenRequest(AuthRequest):
    token: str = Field(min_length=20, max_length=256)


class ResetPasswordRequest(AuthRequest):
    token: str = Field(min_length=20, max_length=256)
    password: str = Field(min_length=1, max_length=4096)


class SafeUser(BaseModel):
    id: UUID
    email: EmailStr
    account_status: str
    email_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthUserResponse(BaseModel):
    user: SafeUser
    development_token: str | None = None


class MessageResponse(BaseModel):
    message: str
    development_token: str | None = None


class SessionResponse(BaseModel):
    user: SafeUser


class CurrentUserResponse(BaseModel):
    user: SafeUser
