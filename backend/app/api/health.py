from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.errors import ServiceUnavailableError
from app.db.readiness import check_database
from app.db.session import Database, get_database
from app.schemas.error import ErrorResponse
from app.schemas.health import DatabaseCheck, HealthResponse, ReadinessChecks, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Liveness: the process is up. Deliberately does not touch the database."""
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/ready", response_model=ReadinessResponse, responses={503: {"model": ErrorResponse}})
def ready(database: Annotated[Database, Depends(get_database)]) -> ReadinessResponse:
    """Readiness: the app and its database can serve traffic."""
    status = check_database(database.engine)
    if not status.reachable:
        raise ServiceUnavailableError(
            code="DATABASE_UNAVAILABLE",
            message="The database is not reachable. Please try again shortly.",
        )
    return ReadinessResponse(
        status="ready",
        checks=ReadinessChecks(database=DatabaseCheck(status="ok", latency_ms=status.latency_ms)),
    )
