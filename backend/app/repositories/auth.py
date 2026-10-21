from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.auth import AuthSession, AuthToken, User
from app.repositories.base import Repository


class UserRepository(Repository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email))


class AuthSessionRepository(Repository[AuthSession]):
    model = AuthSession

    def get_active(self, token_hash: str, *, now: datetime) -> AuthSession | None:
        return self.session.scalar(
            select(AuthSession).where(
                AuthSession.token_hash == token_hash,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
        )

    def revoke(self, session: AuthSession, *, now: datetime | None = None) -> None:
        session.revoked_at = now or datetime.now(timezone.utc)
        self.session.flush()

    def revoke_all_for_user(self, user_id: UUID, *, now: datetime | None = None) -> None:
        self.session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now or datetime.now(timezone.utc))
        )


class AuthTokenRepository(Repository[AuthToken]):
    model = AuthToken

    def consume_active(self, token_hash: str, purpose: str, *, now: datetime) -> AuthToken | None:
        statement = (
            update(AuthToken)
            .where(
                AuthToken.token_hash == token_hash,
                AuthToken.purpose == purpose,
                AuthToken.consumed_at.is_(None),
                AuthToken.expires_at > now,
            )
            .values(consumed_at=now)
            .returning(AuthToken)
        )
        return self.session.scalar(statement)

    def invalidate_for_user(self, user_id: UUID, purpose: str) -> None:
        self.session.execute(
            update(AuthToken)
            .where(
                AuthToken.user_id == user_id,
                AuthToken.purpose == purpose,
                AuthToken.consumed_at.is_(None),
            )
            .values(consumed_at=datetime.now(timezone.utc))
        )
