from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.api.dependencies.auth import require_authenticated_user
from app.db.session import DbSession
from app.models.auth import User
from app.schemas.ledger import LedgerTransactionResponse
from app.services.ledger import LedgerService

router = APIRouter(prefix="/ledger", tags=["ledger"])


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get(
    "/{transaction_id}",
    response_model=LedgerTransactionResponse,
    summary="Get a posted ledger transaction visible to the current user",
)
def get_ledger_transaction(
    transaction_id: UUID,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> LedgerTransactionResponse:
    _no_store(response)
    return LedgerService(session).get_transaction(transaction_id, user)


__all__ = ["router"]
