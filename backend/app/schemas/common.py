from typing import Any, Literal

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class Envelope[T](BaseModel):
    data: T | None = None
    error: ErrorDetail | None = None


def ok[T](data: T) -> dict[str, Any]:
    """Wrap a successful payload in the standard {data, error} envelope."""
    return {"data": data, "error": None}


def fail(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Wrap an error payload in the standard {data, error} envelope."""
    return {
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }


class HealthChecks(BaseModel):
    database: Literal["ok", "error"]
    llm: Literal["ok", "degraded", "error"]


class HealthData(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    checks: HealthChecks
    uptime_seconds: int
