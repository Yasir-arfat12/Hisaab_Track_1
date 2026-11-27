import math
import time
from collections import defaultdict, deque
from typing import ClassVar

from fastapi import status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.auth.session import decode_session_token
from app.config import settings
from app.schemas.common import fail
from app.utils.exceptions import AppError, ErrorCode

# (max_requests, window_seconds)
_ENDPOINT_LIMITS: dict[tuple[str, str], tuple[int, int]] = {
    ("POST", "/api/v1/gmail/sync"): (5, 3600),
    ("POST", "/api/v1/credits/upload"): (10, 3600),
    ("POST", "/api/v1/auth/demo"): (30, 3600),
}
_DEFAULT_LIMIT = (120, 60)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-free in-memory sliding-window rate limiter per user (or client IP)."""

    _buckets: ClassVar[dict[str, deque[float]]] = defaultdict(deque)
    enabled: bool = True

    @classmethod
    def reset(cls) -> None:
        cls._buckets.clear()

    @classmethod
    def _resolve_subject(cls, request: Request) -> str:
        token = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if token:
            try:
                return f"user:{decode_session_token(token)}"
            except AppError:
                pass
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    @classmethod
    def _resolve_limit(cls, method: str, path: str) -> tuple[int, int]:
        if (method, path) in _ENDPOINT_LIMITS:
            return _ENDPOINT_LIMITS[(method, path)]
        if method == "POST" and path.startswith("/api/v1/escalation/") and path.endswith("/draft"):
            return (20, 3600)
        return _DEFAULT_LIMIT

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self.enabled or request.url.path == "/api/v1/health":
            return await call_next(request)

        max_reqs, window_sec = self._resolve_limit(request.method, request.url.path)
        subject = self._resolve_subject(request)
        bucket_key = f"{subject}:{request.method}:{request.url.path}"

        now = time.monotonic()
        cutoff = now - window_sec
        dq = self._buckets[bucket_key]
        while dq and dq[0] <= cutoff:
            dq.popleft()

        if len(dq) >= max_reqs:
            retry_after = max(1, math.ceil(dq[0] + window_sec - now))
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(retry_after)},
                content=fail(
                    code=ErrorCode.RATE_LIMITED,
                    message="Too many requests",
                    details={"retry_after_seconds": retry_after},
                ),
            )

        dq.append(now)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach standard HTTP security headers to every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if settings.ENVIRONMENT == "prod":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
