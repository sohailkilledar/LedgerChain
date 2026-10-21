from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.api.dependencies.auth import require_allowed_origin, require_authenticated_user, require_csrf_token
from app.core.config import Settings, get_settings
from app.core.errors import NotFoundError
from app.db.session import DbSession
from app.models.asset import Asset, AssetEvent
from app.models.auth import User
from app.schemas.asset import (
    AssetCreate,
    AssetEventResponse,
    AssetHistoryResponse,
    AssetOwnershipPage,
    AssetOwnershipResponse,
    AssetPage,
    AssetResponse,
    AssetStatusChange,
    AssetTransfer,
    AssetVerificationResponse,
    CustodyChange,
    ProductCreate,
    ProductPage,
    ProductResponse,
)
from app.schemas.blockchain import BlockchainRecordResponse
from app.services.asset import AssetService
from app.services.blockchain import BlockchainService

router = APIRouter(tags=["supply chain"])
_mutation_dependencies = [Depends(require_csrf_token), Depends(require_allowed_origin)]


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


def _asset_response(asset: Asset) -> AssetResponse:
    return AssetResponse(
        id=asset.id,
        organization_id=asset.organization_id,
        product_id=asset.product_id,
        asset_identifier=asset.asset_identifier,
        category=asset.category,
        name=asset.name,
        description=asset.description,
        metadata=asset.metadata_json,
        current_owner_organization_id=asset.current_owner_organization_id,
        current_custodian_organization_id=asset.current_custodian_organization_id,
        status=asset.status,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def _event_response(event: AssetEvent) -> AssetEventResponse:
    return AssetEventResponse(
        id=event.id,
        asset_id=event.asset_id,
        sequence_number=event.sequence_number,
        event_type=event.event_type,
        actor_user_id=event.actor_user_id,
        actor_organization_id=event.actor_organization_id,
        previous_state=event.previous_state,
        resulting_state=event.resulting_state,
        metadata=event.metadata_json,
        created_at=event.created_at,
    )


@router.post(
    "/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED,
    dependencies=_mutation_dependencies, summary="Create a product for an organization",
)
def create_product(
    payload: ProductCreate, response: Response, session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> ProductResponse:
    _no_store(response)
    return ProductResponse.model_validate(AssetService(session).create_product(user, payload))


@router.get("/products", response_model=ProductPage, summary="List products visible to the current user")
def list_products(
    response: Response, session: DbSession, user: Annotated[User, Depends(require_authenticated_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> ProductPage:
    _no_store(response)
    items, has_more = AssetService(session).list_products(user, limit=limit, offset=offset)
    return ProductPage(items=[ProductResponse.model_validate(item) for item in items], limit=limit, offset=offset, has_more=has_more)


@router.get("/products/{product_id}", response_model=ProductResponse, summary="Get a visible product")
def get_product(
    product_id: UUID, response: Response, session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> ProductResponse:
    _no_store(response)
    return ProductResponse.model_validate(AssetService(session).get_product(product_id, user))


@router.post(
    "/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED,
    dependencies=_mutation_dependencies, summary="Register an individually tracked asset",
)
def create_asset(
    payload: AssetCreate, response: Response, session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> AssetResponse:
    _no_store(response)
    return _asset_response(AssetService(session).create_asset(user, payload))


@router.get("/assets", response_model=AssetPage, summary="List assets visible to the current user")
def list_assets(
    response: Response, session: DbSession, user: Annotated[User, Depends(require_authenticated_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> AssetPage:
    _no_store(response)
    items, has_more = AssetService(session).list_assets(user, limit=limit, offset=offset)
    return AssetPage(items=[_asset_response(item) for item in items], limit=limit, offset=offset, has_more=has_more)


@router.get("/assets/{asset_id}", response_model=AssetResponse, summary="Get an asset visible to the current user")
def get_asset(
    asset_id: UUID, response: Response, session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> AssetResponse:
    _no_store(response)
    return _asset_response(AssetService(session).get_asset(asset_id, user))


@router.post(
    "/assets/{asset_id}/transfer", response_model=AssetEventResponse,
    dependencies=_mutation_dependencies, summary="Transfer asset ownership",
)
def transfer_asset(
    asset_id: UUID, payload: AssetTransfer, response: Response, session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> AssetEventResponse:
    _no_store(response)
    return _event_response(AssetService(session).transfer(asset_id, user, payload, idempotency_key.strip()))


@router.post(
    "/assets/{asset_id}/custody", response_model=AssetEventResponse,
    dependencies=_mutation_dependencies, summary="Change an asset's custodian",
)
def change_asset_custody(
    asset_id: UUID, payload: CustodyChange, response: Response, session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> AssetEventResponse:
    _no_store(response)
    return _event_response(AssetService(session).change_custody(asset_id, user, payload, idempotency_key.strip()))


@router.post(
    "/assets/{asset_id}/retire", response_model=AssetEventResponse,
    dependencies=_mutation_dependencies, summary="Retire an active asset",
)
def retire_asset(
    asset_id: UUID, payload: AssetStatusChange, response: Response, session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> AssetEventResponse:
    _no_store(response)
    return _event_response(AssetService(session).retire(asset_id, user, idempotency_key.strip()))


@router.get("/assets/{asset_id}/history", response_model=AssetHistoryResponse, summary="Read a page of append-only asset provenance")
def get_asset_history(
    asset_id: UUID, response: Response, session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> AssetHistoryResponse:
    _no_store(response)
    events, has_more = AssetService(session).history(asset_id, user, limit=limit, offset=offset)
    return AssetHistoryResponse(
        asset_id=asset_id,
        items=[_event_response(event) for event in events],
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.get("/assets/{asset_id}/ownership", response_model=AssetOwnershipPage, summary="Read a page of asset ownership history")
def get_asset_ownership(
    asset_id: UUID, response: Response, session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> AssetOwnershipPage:
    _no_store(response)
    ownerships, has_more = AssetService(session).ownership_history(asset_id, user, limit=limit, offset=offset)
    return AssetOwnershipPage(
        items=[AssetOwnershipResponse.model_validate(item) for item in ownerships],
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.get("/assets/{asset_id}/verify", response_model=AssetVerificationResponse, summary="Check asset history consistency and anchors")
def verify_asset(
    asset_id: UUID, response: Response, session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AssetVerificationResponse:
    _no_store(response)
    service = AssetService(session)
    result = service.verification(asset_id, user)
    event_id = result["latest_anchor_record_event_id"]
    if isinstance(event_id, UUID):
        blockchain_result = BlockchainService(session, settings).verify_asset_event(event_id, user)
        result.update(blockchain_result)
        result["integrity_warning"] = bool(result["integrity_warning"] or blockchain_result["integrity_warning"])
    return AssetVerificationResponse.model_validate(result)


@router.post(
    "/assets/{asset_id}/history/{event_id}/anchor",
    response_model=BlockchainRecordResponse,
    dependencies=_mutation_dependencies,
    summary="Anchor a canonical asset provenance event",
)
def anchor_asset_event(
    asset_id: UUID, event_id: UUID, response: Response, session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BlockchainRecordResponse:
    _no_store(response)
    event = AssetService(session).event(event_id, user)
    if event.asset_id != asset_id:
        raise NotFoundError("The asset event was not found.", code="ASSET_EVENT_NOT_FOUND")
    return BlockchainService(session, settings).anchor_asset_event(event_id, user)


__all__ = ["router"]


