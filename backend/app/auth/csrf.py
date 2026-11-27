import hmac

from fastapi import status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.schemas.common import fail
from app.utils.exceptions import ErrorCode

STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class CSRFMiddleware(BaseHTTPMiddleware):
    """Enforce double-submit CSRF token on authenticated state-changing requests."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in STATE_CHANGING_METHODS:
            has_session = settings.SESSION_COOKIE_NAME in request.cookies
            if has_session:
                csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME, "")
                csrf_header = request.headers.get("X-CSRF-Token", "")
                if (
                    not csrf_cookie
                    or not csrf_header
                    or not hmac.compare_digest(csrf_cookie, csrf_header)
                ):
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content=fail(
                            code=ErrorCode.VALIDATION_ERROR,
                            message="CSRF token missing or invalid",
                        ),
                    )
        return await call_next(request)
