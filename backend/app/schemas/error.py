from pydantic import BaseModel


class FieldError(BaseModel):
    field: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    retryable: bool = False
    committed: bool = False
    fields: list[FieldError] | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
