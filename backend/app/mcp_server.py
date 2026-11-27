from contextvars import ContextVar
from typing import Any
from uuid import UUID

from fastmcp import FastMCP
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app import database
from app.auth.session import decode_session_token
from app.config import settings
from app.schemas.common import fail
from app.services import (
    dossier_service,
    escalation_service,
    extraction_service,
    merchant_service,
    verification_service,
)
from app.utils.exceptions import AppError, ErrorCode

mcp = FastMCP("Hisaab MCP Server")

_current_mcp_user_id: ContextVar[UUID | None] = ContextVar("_current_mcp_user_id", default=None)


def set_mcp_user_id(user_id: UUID | None):
    """Set the authenticated user ID in the current async context."""
    return _current_mcp_user_id.set(user_id)


def _require_mcp_user_id() -> UUID:
    user_id = _current_mcp_user_id.get()
    if user_id is None:
        raise ValueError("AUTH_REQUIRED: Missing authenticated MCP user context")
    return user_id


@mcp.tool()
async def extract_promises(email_text: str) -> list[dict[str, Any]]:
    """Read-only preview: extract and validate promise candidates from email text."""
    _require_mcp_user_id()
    async with database.async_session_factory() as db:
        candidates = await extraction_service.extract_promises(email_text, db=db)
    return [
        {
            "merchant": c.merchant,
            "amount_paise": c.amount_paise,
            "due_date": c.due_date.isoformat() if c.due_date else None,
            "exact_quote": c.exact_quote,
            "confidence": c.confidence,
            "category": c.category,
            "status": c.status,
            "extraction_method": c.extraction_method,
            "needs_review_reason": c.needs_review_reason,
        }
        for c in candidates
    ]


@mcp.tool()
async def verify_fulfillment(promise_id: str) -> dict[str, Any]:
    """Deterministically verify a promise against bank credits."""
    user_id = _require_mcp_user_id()
    async with database.async_session_factory() as db:
        result = await verification_service.verify_fulfillment(db, user_id, UUID(promise_id))
    return result.model_dump(mode="json")


@mcp.tool()
async def next_escalation_step(promise_id: str) -> dict[str, Any]:
    """Compute the deterministic next escalation rung and IST deadline for a promise."""
    user_id = _require_mcp_user_id()
    async with database.async_session_factory() as db:
        result = await escalation_service.get_next_escalation_step(db, user_id, UUID(promise_id))
    return result.model_dump(mode="json")


@mcp.tool()
async def build_dossier(promise_id: str) -> dict[str, Any]:
    """Build a structured JSON evidence dossier summary for a promise."""
    user_id = _require_mcp_user_id()
    async with database.async_session_factory() as db:
        return await dossier_service.build_dossier_summary(db, user_id, UUID(promise_id))


@mcp.tool()
async def check_merchant_record(merchant_id: str) -> dict[str, Any]:
    """Check promise-keeping statistics for a merchant from the user's records."""
    user_id = _require_mcp_user_id()
    async with database.async_session_factory() as db:
        result = await merchant_service.get_merchant_record(db, user_id, UUID(merchant_id))
    return result.model_dump(mode="json")


class MCPAuthMiddleware:
    """ASGI middleware enforcing Bearer JWT or session cookie auth on /mcp."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        token: str | None = None
        auth_header = headers.get(b"authorization", b"").decode("latin-1")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

        if not token:
            cookie_header = headers.get(b"cookie", b"").decode("latin-1")
            for part in cookie_header.split(";"):
                if "=" in part:
                    k, v = part.strip().split("=", 1)
                    if k == settings.SESSION_COOKIE_NAME:
                        token = v
                        break

        if not token:
            resp = JSONResponse(
                status_code=401,
                content=fail(ErrorCode.AUTH_REQUIRED, "Authentication required"),
            )
            await resp(scope, receive, send)
            return

        try:
            user_id = decode_session_token(token)
        except AppError as exc:
            resp = JSONResponse(
                status_code=exc.status_code,
                content=fail(exc.detail.code, exc.detail.message),
            )
            await resp(scope, receive, send)
            return

        ctx_token = set_mcp_user_id(user_id)
        try:
            await self.app(scope, receive, send)
        finally:
            _current_mcp_user_id.reset(ctx_token)


mcp_http_app = mcp.http_app(path="/")
mcp_asgi_app = MCPAuthMiddleware(mcp_http_app)
