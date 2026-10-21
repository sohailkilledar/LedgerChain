from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AuthenticationError, ConflictError, ValidationError
from app.core.passwords import PasswordService
from app.models.account import NotificationPreferences, Organization, OrganizationMembership, UserSettings
from app.models.auth import AuthSession, AuthToken, User
from app.repositories.auth import AuthSessionRepository, AuthTokenRepository, UserRepository

EMAIL_VERIFICATION_TTL = timedelta(hours=24)
PASSWORD_RESET_TTL = timedelta(minutes=30)
SESSION_TTL = timedelta(hours=12)
REMEMBERED_SESSION_TTL = timedelta(days=30)
GENERIC_RESET_MESSAGE = "If an account exists for this email, reset instructions will be sent shortly."
GENERIC_RESEND_MESSAGE = "If an account needs verification, verification instructions will be sent shortly."


def normalize_email(value: str) -> str:
    try:
        validated = validate_email(value.strip(), check_deliverability=False)
    except EmailNotValidError as exc:
        raise ValidationError("Enter a valid email address.", code="INVALID_EMAIL") from exc
    return validated.normalized.casefold()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()



def _raw_token() -> str:
    return secrets.token_urlsafe(32)


@dataclass(frozen=True)
class LoginResult:
    user: User
    session_token: str
    csrf_token: str
    expires_at: datetime


@dataclass(frozen=True)
class AuthResult:
    user: User
    development_token: str | None = None


class AuthService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)
        self.sessions = AuthSessionRepository(session)
        self.tokens = AuthTokenRepository(session)

    def register(
        self,
        email: str,
        password: str,
        display_name: str | None = None,
        organization_name: str | None = None,
    ) -> AuthResult:
        PasswordService.validate(password)
        normalized_email = normalize_email(email)
        if self.users.get_by_email(normalized_email):
            raise ConflictError("An account with this email already exists.", code="EMAIL_ALREADY_REGISTERED")

        user = User(
            email=normalized_email,
            password_hash=PasswordService.hash(password),
            display_name=display_name or None,
            email_verified=True,
        )
        try:
            self.session.add(user)
            self.session.flush()
            organization = Organization(name=organization_name or "My organization")
            self.session.add(organization)
            self.session.flush()
            self.session.add_all(
                [
                    OrganizationMembership(organization_id=organization.id, user_id=user.id, role="owner"),
                    UserSettings(user_id=user.id),
                    NotificationPreferences(user_id=user.id),
                ]
            )
            self.session.commit()
            self.session.refresh(user)
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("An account with this email already exists.", code="EMAIL_ALREADY_REGISTERED") from exc
        return AuthResult(user=user)

    def login(self, email: str, password: str, remember: bool) -> LoginResult:
        normalized_email = normalize_email(email)
        user = self.users.get_by_email(normalized_email)
        valid_password = PasswordService.verify(password, user.password_hash if user else None)
        if not valid_password or user is None:
            raise AuthenticationError("Email or password is incorrect.", code="INVALID_CREDENTIALS")
        if user.account_status != "active":
            raise AuthenticationError("Email or password is incorrect.", code="INVALID_CREDENTIALS")

        now = datetime.now(timezone.utc)
        expires_at = now + (REMEMBERED_SESSION_TTL if remember else SESSION_TTL)
        raw_session_token = _raw_token()
        raw_csrf_token = _raw_token()
        auth_session = AuthSession(
            user_id=user.id,
            token_hash=hash_token(raw_session_token),
            csrf_token_hash=hash_token(raw_csrf_token),
            expires_at=expires_at,
        )
        self.sessions.add(auth_session)
        self.session.commit()
        return LoginResult(user, raw_session_token, raw_csrf_token, expires_at)

    def logout(self, auth_session: AuthSession) -> None:
        self.sessions.revoke(auth_session)
        self.session.commit()

    def verify_email(self, raw_token: str) -> User:
        now = datetime.now(timezone.utc)
        token = self.tokens.consume_active(hash_token(raw_token), "email_verification", now=now)
        if token is None:
            raise ValidationError("This verification link is invalid or expired.", code="INVALID_OR_EXPIRED_TOKEN")
        user = self.users.get(token.user_id)
        if user is None:
            raise ValidationError("This verification link is invalid or expired.", code="INVALID_OR_EXPIRED_TOKEN")
        user.email_verified = True
        user.updated_at = now
        self.session.commit()
        return user

    def resend_verification(self, email: str) -> str:
        normalized_email = normalize_email(email)
        user = self.users.get_by_email(normalized_email)
        raw_token = _raw_token()
        if user is not None and user.account_status == "active" and not user.email_verified:
            self._issue_token(user.id, "email_verification", raw_token, EMAIL_VERIFICATION_TTL)
            self.session.commit()
        return raw_token

    def request_password_reset(self, email: str) -> str:
        normalized_email = normalize_email(email)
        user = self.users.get_by_email(normalized_email)
        raw_token = _raw_token()
        if user is not None and user.account_status == "active":
            self._issue_token(user.id, "password_reset", raw_token, PASSWORD_RESET_TTL)
            self.session.commit()
        return raw_token

    def reset_password(self, raw_token: str, password: str) -> User:
        PasswordService.validate(password)
        now = datetime.now(timezone.utc)
        token = self.tokens.consume_active(hash_token(raw_token), "password_reset", now=now)
        if token is None:
            raise ValidationError("This password reset link is invalid or expired.", code="INVALID_OR_EXPIRED_TOKEN")
        user = self.users.get(token.user_id)
        if user is None or user.account_status != "active":
            raise ValidationError("This password reset link is invalid or expired.", code="INVALID_OR_EXPIRED_TOKEN")

        user.password_hash = PasswordService.hash(password)
        user.updated_at = now
        self.tokens.invalidate_for_user(user.id, "password_reset")
        self.sessions.revoke_all_for_user(user.id, now=now)
        self.session.commit()
        return user

    def _issue_token(self, user_id: UUID, purpose: str, raw_token: str, ttl: timedelta) -> None:
        self.tokens.invalidate_for_user(user_id, purpose)
        self.tokens.add(
            AuthToken(
                user_id=user_id,
                purpose=purpose,
                token_hash=hash_token(raw_token),
                expires_at=datetime.now(timezone.utc) + ttl,
            )
        )
