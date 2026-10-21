from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.api.dependencies.auth import require_allowed_origin, require_authenticated_user, require_csrf_token
from app.core.config import Settings, get_settings
from app.core.errors import NotFoundError
from app.db.session import DbSession
from app.models.auth import User
from app.models.supply_chain import InventoryShipmentEvent
from app.schemas.blockchain import (
    BlockchainRecordResponse,
    BlockchainStatusResponse,
    BlockchainVerificationResponse,
    ShipmentEventVerificationResponse,
)
from app.services.blockchain import BlockchainService

router = APIRouter(prefix="/blockchain", tags=["blockchain"])
_mutation_dependencies = [Depends(require_csrf_token), Depends(require_allowed_origin)]


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get("/status", response_model=BlockchainStatusResponse, summary="Get blockchain provider health")
def get_blockchain_status(
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BlockchainStatusResponse:
    _no_store(response)
    return BlockchainService(session, settings).status()


@router.post(
    "/ledger/{ledger_transaction_id}/anchor",
    response_model=BlockchainRecordResponse,
    dependencies=_mutation_dependencies,
    summary="Anchor a posted ledger transaction",
)
def anchor_ledger_transaction(
    ledger_transaction_id: UUID,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BlockchainRecordResponse:
    _no_store(response)
    return BlockchainService(session, settings).anchor(ledger_transaction_id, user)


@router.get(
    "/ledger/{ledger_transaction_id}/verify",
    response_model=BlockchainVerificationResponse,
    summary="Verify the current ledger contents against its on-chain anchor",
)
def verify_ledger_transaction(
    ledger_transaction_id: UUID,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BlockchainVerificationResponse:
    _no_store(response)
    return BlockchainService(session, settings).verify(ledger_transaction_id, user)


@router.post(
    "/shipments/{shipment_id}/events/{shipment_event_id}/anchor",
    response_model=BlockchainRecordResponse,
    dependencies=_mutation_dependencies,
    summary="Anchor a shipment dispatch, transit, receipt, or rejection event",
)
def anchor_shipment_event(
    shipment_id: UUID, shipment_event_id: UUID, response: Response, session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BlockchainRecordResponse:
    _no_store(response)
    event = session.get(InventoryShipmentEvent, shipment_event_id)
    if event is None or event.shipment_id != shipment_id:
        raise NotFoundError("The shipment event was not found.", code="SHIPMENT_EVENT_NOT_FOUND")
    return BlockchainService(session, settings).anchor_shipment_event(shipment_event_id, user)


@router.get(
    "/shipments/{shipment_id}/events/{shipment_event_id}/verify",
    response_model=ShipmentEventVerificationResponse,
    summary="Verify shipment history and optional blockchain evidence",
)
def verify_shipment_event(
    shipment_id: UUID, shipment_event_id: UUID, response: Response, session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ShipmentEventVerificationResponse:
    _no_store(response)
    event = session.get(InventoryShipmentEvent, shipment_event_id)
    if event is None or event.shipment_id != shipment_id:
        raise NotFoundError("The shipment event was not found.", code="SHIPMENT_EVENT_NOT_FOUND")
    return BlockchainService(session, settings).verify_shipment_event(shipment_event_id, user)


@router.get(
    "/transactions/{record_id}",
    response_model=BlockchainRecordResponse,
    summary="Get the blockchain anchor for a ledger transaction",
)
def get_blockchain_record(
    record_id: UUID,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BlockchainRecordResponse:
    _no_store(response)
    return BlockchainService(session, settings).get_record(record_id, user)


__all__ = ["router"]
