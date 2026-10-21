from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    environment: str


class DatabaseCheck(BaseModel):
    status: Literal["ok"]
    latency_ms: float | None = None


class ReadinessChecks(BaseModel):
    database: DatabaseCheck


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    checks: ReadinessChecks
