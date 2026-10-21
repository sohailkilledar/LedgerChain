from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.dependencies.auth import require_allowed_origin, require_authenticated_user, require_csrf_token
from app.db.session import DbSession
from app.models.auth import User
from app.schemas.account import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    OrganizationResponse,
    OrganizationUpdate,
    UserProfileResponse,
    UserProfileUpdate,
    UserSettingsResponse,
    UserSettingsUpdate,
)
from app.services.account import AccountService

router = APIRouter(tags=["users and accounts"])
_mutation_dependencies = [Depends(require_csrf_token), Depends(require_allowed_origin)]


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get("/users/me", response_model=UserProfileResponse, summary="Get the current user's profile")
def get_profile(
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> UserProfileResponse:
    _no_store(response)
    return UserProfileResponse.model_validate(AccountService(session).get_profile(user))


@router.patch(
    "/users/me",
    response_model=UserProfileResponse,
    dependencies=_mutation_dependencies,
    summary="Update the current user's profile",
)
def update_profile(
    payload: UserProfileUpdate,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> UserProfileResponse:
    _no_store(response)
    updated = AccountService(session).update_profile(user, payload.model_dump(exclude_unset=True))
    return UserProfileResponse.model_validate(updated)


@router.get("/account", response_model=OrganizationResponse, summary="Get the current organization account")
def get_account(
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> OrganizationResponse:
    _no_store(response)
    organization, membership = AccountService(session).get_account(user.id)
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        account_number=organization.account_number,
        balance=organization.balance,
        account_type=organization.account_type,
        status=organization.status,
        role=membership.role,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
    )


@router.patch(
    "/account",
    response_model=OrganizationResponse,
    dependencies=_mutation_dependencies,
    summary="Update organization account details (owner only)",
)
def update_account(
    payload: OrganizationUpdate,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> OrganizationResponse:
    _no_store(response)
    organization, membership = AccountService(session).update_account(
        user.id, payload.model_dump(exclude_unset=True)
    )
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        account_number=organization.account_number,
        balance=organization.balance,
        account_type=organization.account_type,
        status=organization.status,
        role=membership.role,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
    )


@router.get(
    "/users/me/settings",
    response_model=UserSettingsResponse,
    summary="Get the current user's settings",
)
def get_settings(
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> UserSettingsResponse:
    _no_store(response)
    return UserSettingsResponse.model_validate(AccountService(session).get_settings(user.id))


@router.patch(
    "/users/me/settings",
    response_model=UserSettingsResponse,
    dependencies=_mutation_dependencies,
    summary="Update the current user's settings",
)
def update_settings(
    payload: UserSettingsUpdate,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> UserSettingsResponse:
    _no_store(response)
    updated = AccountService(session).update_settings(user.id, payload.model_dump(exclude_unset=True))
    return UserSettingsResponse.model_validate(updated)


@router.get(
    "/users/me/notifications",
    response_model=NotificationPreferencesResponse,
    summary="Get notification preferences",
)
def get_notifications(
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> NotificationPreferencesResponse:
    _no_store(response)
    return NotificationPreferencesResponse.model_validate(AccountService(session).get_notification_preferences(user.id))


@router.patch(
    "/users/me/notifications",
    response_model=NotificationPreferencesResponse,
    dependencies=_mutation_dependencies,
    summary="Update notification preferences",
)
def update_notifications(
    payload: NotificationPreferencesUpdate,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> NotificationPreferencesResponse:
    _no_store(response)
    updated = AccountService(session).update_notification_preferences(
        user.id, payload.model_dump(exclude_unset=True)
    )
    return NotificationPreferencesResponse.model_validate(updated)


__all__ = ["router"]
