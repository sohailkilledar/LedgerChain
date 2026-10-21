from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.api.dependencies.auth import require_allowed_origin, require_authenticated_user, require_csrf_token
from app.db.session import DbSession
from app.models.auth import User
from app.schemas.finance import (
    BudgetCreate,
    BudgetResponse,
    FinanceBudgetPage,
    PaymentRequestCreate,
    PaymentRequestDecision,
    PaymentRequestEventResponse,
    PaymentRequestHistory,
    PaymentRequestPage,
    PaymentRequestResponse,
)
from app.services.finance import FinanceService

router = APIRouter(prefix="/finance", tags=["finance"])
_mutation_dependencies = [Depends(require_csrf_token), Depends(require_allowed_origin)]


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get("/budgets", response_model=FinanceBudgetPage)
def list_budgets(
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> FinanceBudgetPage:
    _no_store(response)
    items, has_more = FinanceService(session).list_budgets(user, limit=limit, offset=offset)
    return FinanceBudgetPage(items=items, limit=limit, offset=offset, has_more=has_more)


@router.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED, dependencies=_mutation_dependencies)
def create_budget(
    payload: BudgetCreate,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> BudgetResponse:
    _no_store(response)
    return FinanceService(session).create_budget(user, payload)


@router.get("/payment-requests", response_model=PaymentRequestPage)
def list_payment_requests(
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> PaymentRequestPage:
    _no_store(response)
    items, has_more = FinanceService(session).list_requests(user, limit=limit, offset=offset)
    return PaymentRequestPage(items=items, limit=limit, offset=offset, has_more=has_more)


@router.post("/payment-requests", response_model=PaymentRequestResponse, status_code=status.HTTP_201_CREATED, dependencies=_mutation_dependencies)
def create_payment_request(
    payload: PaymentRequestCreate,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> PaymentRequestResponse:
    _no_store(response)
    return FinanceService(session).create_request(user, payload, idempotency_key.strip())


@router.post("/payment-requests/{request_id}/submit", response_model=PaymentRequestResponse, dependencies=_mutation_dependencies)
def submit_payment_request(
    request_id: UUID,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> PaymentRequestResponse:
    _no_store(response)
    return FinanceService(session).submit_request(request_id, user)


@router.post("/payment-requests/{request_id}/approve", response_model=PaymentRequestResponse, dependencies=_mutation_dependencies)
def approve_payment_request(
    request_id: UUID,
    payload: PaymentRequestDecision,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> PaymentRequestResponse:
    _no_store(response)
    return FinanceService(session).decide_request(request_id, user, approve=True, note=payload.note)


@router.post("/payment-requests/{request_id}/reject", response_model=PaymentRequestResponse, dependencies=_mutation_dependencies)
def reject_payment_request(
    request_id: UUID,
    payload: PaymentRequestDecision,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> PaymentRequestResponse:
    _no_store(response)
    return FinanceService(session).decide_request(request_id, user, approve=False, note=payload.note)


@router.post("/payment-requests/{request_id}/execute", response_model=PaymentRequestResponse, dependencies=_mutation_dependencies)
def execute_payment_request(
    request_id: UUID,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> PaymentRequestResponse:
    _no_store(response)
    return FinanceService(session).execute_request(request_id, user)


@router.get("/payment-requests/{request_id}/history", response_model=PaymentRequestHistory)
def payment_request_history(
    request_id: UUID,
    response: Response,
    session: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
) -> PaymentRequestHistory:
    _no_store(response)
    items = FinanceService(session).request_history(request_id, user)
    return PaymentRequestHistory(
        payment_request_id=request_id,
        items=[PaymentRequestEventResponse.model_validate(item) for item in items],
    )


__all__ = ["router"]
