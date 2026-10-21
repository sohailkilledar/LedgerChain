from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.dependencies.auth import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    AuthContext,
    get_auth_service,
    get_optional_auth_context,
    require_allowed_origin,
    require_authenticated_user,
    validate_csrf_token,
)
from app.core.auth_rate_limit import enforce_auth_rate_limit
from app.core.config import Settings, get_settings
from app.db.session import DbSession
from app.models.auth import User
from app.repositories.auth import AuthSessionRepository
from app.schemas.auth import (
    AuthUserResponse,
    CurrentUserResponse,
    EmailRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    SafeUser,
    SessionResponse,
    TokenRequest,
)
from app.services.auth import AuthService, GENERIC_RESEND_MESSAGE, GENERIC_RESET_MESSAGE, LoginResult

router = APIRouter(prefix="/auth", tags=["authentication"])
_auth_post_origin = [Depends(require_allowed_origin)]


def _cookie_options(settings: Settings) -> dict[str, object]:
    return {"secure": settings.is_production, "samesite": "lax", "path": "/"}


def _set_session_cookies(response: Response, result: LoginResult, settings: Settings, remember: bool) -> None:
    from datetime import datetime, timezone

    max_age = int((result.expires_at - datetime.now(timezone.utc)).total_seconds()) if remember else None
    options = _cookie_options(settings)
    response.set_cookie(SESSION_COOKIE, result.session_token, max_age=max_age, httponly=True, **options)
    response.set_cookie(CSRF_COOKIE, result.csrf_token, max_age=max_age, httponly=False, **options)


def _clear_session_cookies(response: Response, settings: Settings) -> None:
    options = _cookie_options(settings)
    response.delete_cookie(SESSION_COOKIE, httponly=True, **options)
    response.delete_cookie(CSRF_COOKIE, httponly=False, **options)


def _development_token_settings(settings: Settings) -> bool:
    return settings.environment in {"development", "test"}


@router.post(
    "/register",
    response_model=AuthUserResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    dependencies=_auth_post_origin,
    summary="Create a LedgerChain account",
)
def register(
    payload: RegisterRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthUserResponse:
    enforce_auth_rate_limit(request, "register", limit=5, window_seconds=3600)
    result = service.register(
        str(payload.email),
        payload.password,
        display_name=payload.display_name,
        organization_name=payload.organization_name,
    )
    return AuthUserResponse(user=SafeUser.model_validate(result.user), development_token=result.development_token)


@router.post(
    "/login",
    response_model=SessionResponse,
    dependencies=_auth_post_origin,
    summary="Sign in and create a secure session",
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionResponse:
    enforce_auth_rate_limit(request, "login", limit=10, window_seconds=900)
    result = service.login(str(payload.email), payload.password, payload.remember)
    _set_session_cookies(response, result, settings, payload.remember)
    return SessionResponse(user=SafeUser.model_validate(result.user))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=_auth_post_origin,
    summary="Revoke the current session",
)
def logout(
    request: Request,
    response: Response,
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[AuthContext | None, Depends(get_optional_auth_context)],
) -> Response:
    if context is not None:
        validate_csrf_token(request, context)
        AuthSessionRepository(session).revoke(context.session)
        session.commit()
    _clear_session_cookies(response, settings)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=CurrentUserResponse, summary="Get the signed-in account")
def me(user: Annotated[User, Depends(require_authenticated_user)]) -> CurrentUserResponse:
    return CurrentUserResponse(user=SafeUser.model_validate(user))


@router.post(
    "/verify-email",
    response_model=AuthUserResponse,
    response_model_exclude_none=True,
    dependencies=_auth_post_origin,
    summary="Verify an email address",
)
def verify_email(
    payload: TokenRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthUserResponse:
    user = service.verify_email(payload.token)
    return AuthUserResponse(user=SafeUser.model_validate(user))


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    response_model_exclude_none=True,
    dependencies=_auth_post_origin,
    summary="Resend email verification instructions",
)
def resend_verification(
    payload: EmailRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MessageResponse:
    enforce_auth_rate_limit(request, "resend-verification", limit=5, window_seconds=3600)
    token = service.resend_verification(str(payload.email))
    development_token = token if _development_token_settings(settings) else None
    return MessageResponse(message=GENERIC_RESEND_MESSAGE, development_token=development_token)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    response_model_exclude_none=True,
    dependencies=_auth_post_origin,
    summary="Request password reset instructions",
)
def forgot_password(
    payload: EmailRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MessageResponse:
    enforce_auth_rate_limit(request, "forgot-password", limit=5, window_seconds=3600)
    token = service.request_password_reset(str(payload.email))
    development_token = token if _development_token_settings(settings) else None
    return MessageResponse(message=GENERIC_RESET_MESSAGE, development_token=development_token)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    dependencies=_auth_post_origin,
    summary="Reset a password using a one-time token",
)
def reset_password(
    payload: ResetPasswordRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    service.reset_password(payload.token, payload.password)
    return MessageResponse(message="Password updated. Sign in with your new password.")
