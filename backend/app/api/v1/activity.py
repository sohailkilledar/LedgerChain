from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response

from app.api.dependencies.auth import require_authenticated_user
from app.db.session import DbSession
from app.models.auth import User
from app.schemas.ledger import ActivityPage
from app.services.ledger import LedgerService

router = APIRouter(tags=["activity"])


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get("/activity", response_model=ActivityPage, summary="List organization-scoped finance, inventory, asset, and blockchain activity")
def list_activity(
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
    activity_type: Annotated[Literal["payment", "finance", "inventory", "shipment", "asset", "blockchain"] | None, Query(alias="type")] = None,
) -> ActivityPage:
    _no_store(response)
    return LedgerService(session).list_activity(
        user, limit=limit, offset=offset, activity_type=activity_type
    )


__all__ = ["router"]
