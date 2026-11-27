from enum import StrEnum
from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.schemas.common import ErrorDetail, fail

logger = structlog.get_logger(__name__)


class ErrorCode(StrEnum):
    AUTH_REQUIRED = "AUTH_REQUIRED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    GMAIL_AUTH_EXPIRED = "GMAIL_AUTH_EXPIRED"
    GMAIL_SCOPE_INSUFFICIENT = "GMAIL_SCOPE_INSUFFICIENT"
    SYNC_IN_PROGRESS = "SYNC_IN_PROGRESS"
    PROMISE_NOT_FOUND = "PROMISE_NOT_FOUND"
    CREDIT_UPLOAD_FAILED = "CREDIT_UPLOAD_FAILED"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    DOSSIER_GENERATION_FAILED = "DOSSIER_GENERATION_FAILED"
    MERCHANT_NOT_FOUND = "MERCHANT_NOT_FOUND"
    DUPLICATE_EMAIL = "DUPLICATE_EMAIL"
    INVALID_IDEMPOTENCY_KEY = "INVALID_IDEMPOTENCY_KEY"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    """Domain/API exception serialized into the standard {data: null, error} envelope."""

    def __init__(
        self,
        code: ErrorCode | str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.detail = ErrorDetail(
            code=str(code),
            message=message,
            details=details or {},
        )
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers enforcing the {data, error} envelope."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "app.error",
            code=exc.detail.code,
            status_code=exc.status_code,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=fail(
                code=exc.detail.code,
                message=exc.detail.message,
                details=exc.detail.details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning("request.validation_error", path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=fail(
                code=ErrorCode.VALIDATION_ERROR,
                message="Request validation failed",
                details={"errors": exc.errors()},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = ErrorCode.NOT_FOUND if exc.status_code == 404 else ErrorCode.VALIDATION_ERROR
        if exc.status_code == 401:
            code = ErrorCode.AUTH_REQUIRED
        elif exc.status_code == 429:
            code = ErrorCode.RATE_LIMITED
        return JSONResponse(
            status_code=exc.status_code,
            content=fail(code=code, message=str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled.exception", path=request.url.path)
        message = str(exc) if settings.ENVIRONMENT == "dev" else "Internal server error"
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=fail(code=ErrorCode.INTERNAL_ERROR, message=message),
        )
