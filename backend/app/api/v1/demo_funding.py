from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response, status

from app.api.dependencies.auth import require_allowed_origin, require_authenticated_user, require_csrf_token
from app.db.session import DbSession
from app.models.auth import User
from app.schemas.demo_funding import DemoFundingCreate, DemoFundingResponse
from app.services.demo_funding import DemoFundingService

router = APIRouter(prefix="/demo-fundings", tags=["demo funding"])


@router.post(
    "/demo",
    response_model=DemoFundingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf_token), Depends(require_allowed_origin)],
    summary="Approve a simulated bank funding request",
)
def create_demo_funding(
    payload: DemoFundingCreate,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> DemoFundingResponse:
    response.headers["Cache-Control"] = "no-store"
    return DemoFundingService(session).create(user, payload, idempotency_key.strip())


__all__ = ["router"]

