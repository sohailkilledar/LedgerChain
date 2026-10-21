from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AuthenticationError, AuthorizationError
from app.db.session import DbSession
from app.models.auth import AuthSession, User
from app.repositories.auth import AuthSessionRepository, UserRepository
from app.services.auth import AuthService, hash_token

SESSION_COOKIE = "ledgerchain_session"
CSRF_COOKIE = "ledgerchain_csrf"
CSRF_HEADER = "X-CSRF-Token"


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: AuthSession


def get_auth_service(
    session: DbSession, settings: Annotated[Settings, Depends(get_settings)]
) -> AuthService:
    return AuthService(session, settings)


def _resolve_context(request: Request, session: Session) -> AuthContext | None:
    raw_token = request.cookies.get(SESSION_COOKIE)
    if not raw_token:
        return None
    auth_session = AuthSessionRepository(session).get_active(
        hash_token(raw_token), now=datetime.now(timezone.utc)
    )
    if auth_session is None:
        return None
    user = UserRepository(session).get(auth_session.user_id)
    if user is None or user.account_status != "active":
        return None
    return AuthContext(user=user, session=auth_session)


def get_optional_auth_context(request: Request, session: DbSession) -> AuthContext | None:
    return _resolve_context(request, session)


def get_auth_context(
    request: Request,
    session: DbSession,
) -> AuthContext:
    context = _resolve_context(request, session)
    if context is None:
        raise AuthenticationError()
    return context


def require_authenticated_user(context: Annotated[AuthContext, Depends(get_auth_context)]) -> User:
    return context.user


def authorize_resource_owner(user: User, resource_owner_id: object) -> None:
    if user.id != resource_owner_id:
        raise AuthorizationError("You don't have permission to access this resource.", code="RESOURCE_ACCESS_DENIED")


def validate_csrf_token(request: Request, context: AuthContext) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    header_token = request.headers.get(CSRF_HEADER, "")
    if (
        not cookie_token
        or not header_token
        or not hmac.compare_digest(cookie_token, header_token)
        or not hmac.compare_digest(hashlib.sha256(header_token.encode("utf-8")).hexdigest(), context.session.csrf_token_hash)
    ):
        raise AuthorizationError("A valid CSRF token is required.", code="CSRF_VALIDATION_FAILED")


def require_csrf_token(
    request: Request,
    context: Annotated[AuthContext, Depends(get_auth_context)],
) -> AuthContext:
    validate_csrf_token(request, context)
    return context


def require_allowed_origin(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    origin = request.headers.get("origin")
    if origin is not None and origin not in settings.cors_origin_list:
        raise AuthorizationError(f"This request origin ({origin!r}) is not allowed; allowed origins are {settings.cors_origin_list!r}.", code="ORIGIN_NOT_ALLOWED")
