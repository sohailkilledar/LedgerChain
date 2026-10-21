from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import NotificationPreferences, Organization, OrganizationMembership, UserSettings
from app.repositories.base import Repository


class OrganizationRepository(Repository[Organization]):
    model = Organization

    def get_for_user(self, user_id: UUID) -> tuple[Organization, OrganizationMembership] | None:
        statement = (
            select(Organization, OrganizationMembership)
            .join(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
            .where(OrganizationMembership.user_id == user_id)
            .order_by(OrganizationMembership.created_at, Organization.id)
        )
        result = self.session.execute(statement).first()
        return (result[0], result[1]) if result else None


class OrganizationMembershipRepository(Repository[OrganizationMembership]):
    model = OrganizationMembership

    def get_for_user_and_organization(self, user_id: UUID, organization_id: UUID) -> OrganizationMembership | None:
        return self.session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == organization_id,
            )
        )


class UserSettingsRepository(Repository[UserSettings]):
    model = UserSettings

    def get_for_user(self, user_id: UUID) -> UserSettings | None:
        return self.session.scalar(select(UserSettings).where(UserSettings.user_id == user_id))


class NotificationPreferencesRepository(Repository[NotificationPreferences]):
    model = NotificationPreferences

    def get_for_user(self, user_id: UUID) -> NotificationPreferences | None:
        return self.session.scalar(select(NotificationPreferences).where(NotificationPreferences.user_id == user_id))


__all__ = [
    "NotificationPreferencesRepository",
    "OrganizationMembershipRepository",
    "OrganizationRepository",
    "UserSettingsRepository",
]
