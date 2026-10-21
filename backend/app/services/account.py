from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AuthorizationError, NotFoundError
from app.models.account import NotificationPreferences, Organization, OrganizationMembership, UserSettings
from app.models.auth import User
from app.repositories.account import (
    NotificationPreferencesRepository,
    OrganizationRepository,
    UserSettingsRepository,
)


class AccountService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.organizations = OrganizationRepository(session)
        self.settings = UserSettingsRepository(session)
        self.notifications = NotificationPreferencesRepository(session)

    def get_profile(self, user: User) -> User:
        return user

    def update_profile(self, user: User, changes: dict[str, Any]) -> User:
        for field, value in changes.items():
            setattr(user, field, value)
        user.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_account(self, user_id: UUID) -> tuple[Organization, OrganizationMembership]:
        result = self.organizations.get_for_user(user_id)
        if result is None:
            raise NotFoundError("No organization is associated with this account.", code="ACCOUNT_NOT_FOUND")
        organization, membership = result
        if organization.status != "active":
            raise AuthorizationError("This organization is not active.", code="ACCOUNT_INACTIVE")
        return result

    def update_account(self, user_id: UUID, changes: dict[str, Any]) -> tuple[Organization, OrganizationMembership]:
        organization, membership = self.get_account(user_id)
        if membership.role != "owner":
            raise AuthorizationError("Only an organization owner can change account details.", code="OWNER_REQUIRED")
        for field, value in changes.items():
            setattr(organization, field, value)
        organization.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(organization)
        return organization, membership

    def get_settings(self, user_id: UUID) -> UserSettings:
        settings = self.settings.get_for_user(user_id)
        if settings is None:
            raise NotFoundError("Account settings are not available.", code="SETTINGS_NOT_FOUND")
        return settings

    def update_settings(self, user_id: UUID, changes: dict[str, Any]) -> UserSettings:
        settings = self.get_settings(user_id)
        for field, value in changes.items():
            setattr(settings, field, value)
        settings.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(settings)
        return settings

    def get_notification_preferences(self, user_id: UUID) -> NotificationPreferences:
        preferences = self.notifications.get_for_user(user_id)
        if preferences is None:
            raise NotFoundError("Notification preferences are not available.", code="NOTIFICATIONS_NOT_FOUND")
        return preferences

    def update_notification_preferences(self, user_id: UUID, changes: dict[str, Any]) -> NotificationPreferences:
        preferences = self.get_notification_preferences(user_id)
        for field, value in changes.items():
            setattr(preferences, field, value)
        preferences.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(preferences)
        return preferences


__all__ = ["AccountService"]
