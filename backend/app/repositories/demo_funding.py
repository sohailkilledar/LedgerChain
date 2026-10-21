from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.demo_funding import DemoFunding


class DemoFundingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_idempotency_key(self, organization_id: UUID, key: str) -> DemoFunding | None:
        return self.session.scalar(
            select(DemoFunding).where(
                DemoFunding.organization_id == organization_id,
                DemoFunding.idempotency_key == key,
            )
        )


__all__ = ["DemoFundingRepository"]

