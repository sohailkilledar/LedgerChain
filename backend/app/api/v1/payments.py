from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.api.dependencies.auth import require_allowed_origin, require_authenticated_user, require_csrf_token
from app.db.session import DbSession
from app.models.auth import User
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate, PaymentPage, PaymentResponse
from app.services.payment import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])
_mutation_dependencies = [Depends(require_csrf_token), Depends(require_allowed_origin)]


def _response(payment: Payment) -> PaymentResponse:
    return PaymentResponse(
        id=payment.id,
        reference=payment.reference,
        sender_organization_id=payment.sender_organization_id,
        recipient_organization_id=payment.recipient_organization_id,
        sender_account=payment.sender_account_number,
        recipient_account=payment.recipient_account_number,
        recipient_name=payment.recipient_name,
        amount=payment.amount,
        fee=payment.fee,
        total_debit=payment.total_debit,
        currency=payment.currency,
        purpose=payment.purpose,
        note=payment.note,
        status=payment.status,
        created_at=payment.created_at,
        completed_at=payment.completed_at,
    )


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=_mutation_dependencies,
    summary="Create an internal LedgerChain account payment",
)
def create_payment(
    payload: PaymentCreate,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> PaymentResponse:
    _no_store(response)
    payment = PaymentService(session).create(user, payload, idempotency_key.strip())
    return _response(payment)


@router.get("", response_model=PaymentPage, summary="List payments visible to the current user")
def list_payments(
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> PaymentPage:
    _no_store(response)
    items, has_more = PaymentService(session).list_for_user(user, limit=limit, offset=offset)
    return PaymentPage(items=[_response(item) for item in items], limit=limit, offset=offset, has_more=has_more)


@router.get("/{payment_id}", response_model=PaymentResponse, summary="Get a payment visible to the current user")
def get_payment(
    payment_id: UUID,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> PaymentResponse:
    _no_store(response)
    return _response(PaymentService(session).get(payment_id, user))


__all__ = ["router"]
