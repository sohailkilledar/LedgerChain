from dataclasses import dataclass
from time import perf_counter

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import get_logger

logger = get_logger("app.db")


@dataclass(frozen=True)
class DatabaseStatus:
    reachable: bool
    latency_ms: float | None = None


def check_database(engine: Engine) -> DatabaseStatus:
    """Run ``SELECT 1``. Failure details are logged, never returned to callers."""
    started = perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.warning("database_unreachable", extra={"error_type": type(exc).__name__})
        return DatabaseStatus(reachable=False)
    return DatabaseStatus(reachable=True, latency_ms=round((perf_counter() - started) * 1000, 2))
