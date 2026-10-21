from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.api.dependencies.auth import require_allowed_origin, require_authenticated_user, require_csrf_token
from app.db.session import DbSession
from app.models.auth import User
from app.schemas.inventory import (
    InventoryMovementCreate,
    InventoryMovementPage,
    InventoryMovementResponse,
    InventoryStockPage,
)
from app.services.inventory import InventoryService

router = APIRouter(tags=["inventory"])
_mutation_dependencies = [Depends(require_csrf_token), Depends(require_allowed_origin)]


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get("/inventory/stocks", response_model=InventoryStockPage, summary="List stock controlled by the current user's organizations")
def list_inventory_stocks(
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> InventoryStockPage:
    _no_store(response)
    items, has_more = InventoryService(session).stocks(user, limit=limit, offset=offset)
    return InventoryStockPage(items=items, limit=limit, offset=offset, has_more=has_more)


@router.get("/inventory/movements", response_model=InventoryMovementPage, summary="List immutable inventory movement history")
def list_inventory_movements(
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> InventoryMovementPage:
    _no_store(response)
    items, has_more = InventoryService(session).movements(user, limit=limit, offset=offset)
    return InventoryMovementPage(items=items, limit=limit, offset=offset, has_more=has_more)


@router.post(
    "/inventory/movements",
    response_model=InventoryMovementResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=_mutation_dependencies,
    summary="Record a stock-in, stock-out, movement, or counted adjustment",
)
def create_inventory_movement(
    payload: InventoryMovementCreate,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> InventoryMovementResponse:
    _no_store(response)
    return InventoryService(session).create_movement(user, payload, idempotency_key.strip())


__all__ = ["router"]
