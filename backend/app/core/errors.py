"""Backend error model.

Every error response has the shape ``{"error": ErrorBody}`` where ErrorBody mirrors
the frontend ``LedgerErrorShape`` (code, message, retryable, committed) so the
future HTTP LedgerService can build a ``LedgerError`` directly from it.
Internal details are logged, never returned to the client.
"""

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.schemas.error import ErrorBody, ErrorResponse, FieldError

logger = get_logger("app.errors")


class AppError(Exception):
    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"
    message: str = "Something went wrong. Please try again."
    retryable: bool = False

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        retryable: bool | None = None,
        committed: bool = False,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        if retryable is not None:
            self.retryable = retryable
        self.committed = committed
        super().__init__(self.message)


class ValidationError(AppError):
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    code = "VALIDATION_ERROR"
    message = "Some of the submitted information is invalid."


class AuthenticationError(AppError):
    status_code = HTTPStatus.UNAUTHORIZED
    code = "AUTHENTICATION_REQUIRED"
    message = "Please sign in to continue."


class AuthorizationError(AppError):
    status_code = HTTPStatus.FORBIDDEN
    code = "FORBIDDEN"
    message = "You don't have permission to do that."


class NotFoundError(AppError):
    status_code = HTTPStatus.NOT_FOUND
    code = "NOT_FOUND"
    message = "The requested resource was not found."


class ConflictError(AppError):
    status_code = HTTPStatus.CONFLICT
    code = "CONFLICT"
    message = "This request conflicts with the current state."


class InternalError(AppError):
    retryable = True


class ServiceUnavailableError(AppError):
    status_code = HTTPStatus.SERVICE_UNAVAILABLE
    code = "SERVICE_UNAVAILABLE"
    message = "The service is temporarily unavailable. Please try again shortly."
    retryable = True


_HTTP_STATUS_CODES: dict[int, str] = {
    HTTPStatus.BAD_REQUEST: "BAD_REQUEST",
    HTTPStatus.UNAUTHORIZED: AuthenticationError.code,
    HTTPStatus.FORBIDDEN: AuthorizationError.code,
    HTTPStatus.NOT_FOUND: NotFoundError.code,
    HTTPStatus.METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    HTTPStatus.CONFLICT: ConflictError.code,
    HTTPStatus.TOO_MANY_REQUESTS: "RATE_LIMITED",
    HTTPStatus.SERVICE_UNAVAILABLE: ServiceUnavailableError.code,
}


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _error_response(
    request: Request,
    status_code: int,
    body: ErrorBody,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body.request_id = _request_id(request)
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=body).model_dump(exclude_none=True),
        headers=headers,
    )


async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    log = logger.error if exc.status_code >= 500 else logger.info
    log("app_error", extra={"code": exc.code, "status": exc.status_code, "request_id": _request_id(request)})
    return _error_response(
        request,
        exc.status_code,
        ErrorBody(code=exc.code, message=exc.message, retryable=exc.retryable, committed=exc.committed),
    )


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [
        FieldError(field=".".join(str(part) for part in err.get("loc", ())), message=err.get("msg", "Invalid value"))
        for err in exc.errors()
    ]
    return _error_response(
        request,
        ValidationError.status_code,
        ErrorBody(code=ValidationError.code, message=ValidationError.message, fields=fields),
    )


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _HTTP_STATUS_CODES.get(exc.status_code, "HTTP_ERROR")
    try:
        message = HTTPStatus(exc.status_code).phrase
    except ValueError:
        message = "Request failed."
    headers: dict[str, Any] | None = getattr(exc, "headers", None)
    return _error_response(request, exc.status_code, ErrorBody(code=code, message=message), headers)


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        extra={"request_id": _request_id(request), "exception_type": type(exc).__name__},
    )
    return _error_response(
        request,
        InternalError.status_code,
        ErrorBody(code=InternalError.code, message=InternalError.message, retryable=True),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_unexpected_error)
