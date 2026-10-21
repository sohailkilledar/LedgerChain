from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.api.dependencies.auth import require_allowed_origin, require_authenticated_user, require_csrf_token
from app.db.session import DbSession
from app.models.auth import User
from app.schemas.supply_chain import (
    InventoryBatchCreate,
    InventoryBatchResponse,
    InventoryShipmentCreate,
    InventoryShipmentPage,
    InventoryShipmentReceive,
    InventoryShipmentReject,
    InventoryShipmentResponse,
)
from app.services.supply_chain import SupplyChainService

router = APIRouter(prefix="/inventory", tags=["supply-chain"])
_mutation_dependencies = [Depends(require_csrf_token), Depends(require_allowed_origin)]


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get("/batches", response_model=list[InventoryBatchResponse])
def list_inventory_batches(
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> list[InventoryBatchResponse]:
    _no_store(response)
    items, _ = SupplyChainService(session).list_batches(user, limit=limit, offset=offset)
    return items


@router.post("/batches", response_model=InventoryBatchResponse, status_code=status.HTTP_201_CREATED, dependencies=_mutation_dependencies)
def create_inventory_batch(
    payload: InventoryBatchCreate,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> InventoryBatchResponse:
    _no_store(response)
    return SupplyChainService(session).create_batch(user, payload)


@router.get("/shipments", response_model=InventoryShipmentPage)
def list_inventory_shipments(
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> InventoryShipmentPage:
    _no_store(response)
    items, has_more = SupplyChainService(session).list_shipments(user, limit=limit, offset=offset)
    return InventoryShipmentPage(items=items, limit=limit, offset=offset, has_more=has_more)


@router.post("/shipments", response_model=InventoryShipmentResponse, status_code=status.HTTP_201_CREATED, dependencies=_mutation_dependencies)
def create_inventory_shipment(
    payload: InventoryShipmentCreate,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> InventoryShipmentResponse:
    _no_store(response)
    return SupplyChainService(session).create_shipment(user, payload, idempotency_key.strip())


def _transition(
    action: str,
    shipment_id: UUID,
    response: Response,
    session: DbSession,
    user: User,
    idempotency_key: str,
    *,
    receive: InventoryShipmentReceive | None = None,
    reject: InventoryShipmentReject | None = None,
) -> InventoryShipmentResponse:
    _no_store(response)
    return SupplyChainService(session).transition(
        user, shipment_id, action, idempotency_key.strip(), receive=receive, reject=reject
    )


@router.post("/shipments/{shipment_id}/dispatch", response_model=InventoryShipmentResponse, dependencies=_mutation_dependencies)
def dispatch_inventory_shipment(
    shipment_id: UUID,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> InventoryShipmentResponse:
    return _transition("dispatch", shipment_id, response, session, user, idempotency_key)


@router.post("/shipments/{shipment_id}/transit", response_model=InventoryShipmentResponse, dependencies=_mutation_dependencies)
def mark_inventory_shipment_in_transit(
    shipment_id: UUID,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> InventoryShipmentResponse:
    return _transition("transit", shipment_id, response, session, user, idempotency_key)


@router.post("/shipments/{shipment_id}/receive", response_model=InventoryShipmentResponse, dependencies=_mutation_dependencies)
def receive_inventory_shipment(
    shipment_id: UUID,
    payload: InventoryShipmentReceive,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> InventoryShipmentResponse:
    return _transition("receive", shipment_id, response, session, user, idempotency_key, receive=payload)


@router.post("/shipments/{shipment_id}/reject", response_model=InventoryShipmentResponse, dependencies=_mutation_dependencies)
def reject_inventory_shipment(
    shipment_id: UUID,
    payload: InventoryShipmentReject,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> InventoryShipmentResponse:
    return _transition("reject", shipment_id, response, session, user, idempotency_key, reject=payload)


__all__ = ["router"]
