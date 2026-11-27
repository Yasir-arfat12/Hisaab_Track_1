import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import Response, status

from app.config import settings
from app.utils.exceptions import AppError, ErrorCode

ALGORITHM = "HS256"


def create_session_token(
    user_id: UUID,
    secret: str | None = None,
    ttl_seconds: int | None = None,
) -> str:
    now = datetime.now(UTC)
    ttl = ttl_seconds if ttl_seconds is not None else settings.SESSION_TTL_SECONDS
    key = secret if secret is not None else settings.SECRET_KEY.get_secret_value()
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
    }
    return jwt.encode(payload, key, algorithm=ALGORITHM)


def decode_session_token(token: str, secret: str | None = None) -> UUID:
    key = secret if secret is not None else settings.SECRET_KEY.get_secret_value()
    try:
        payload = jwt.decode(token, key, algorithms=[ALGORITHM])
        return UUID(str(payload["sub"]))
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise AppError(
            code=ErrorCode.AUTH_REQUIRED,
            message="Session expired or not found",
            status_code=status.HTTP_401_UNAUTHORIZED,
        ) from exc


def set_session_cookies(response: Response, user_id: UUID) -> str:
    """Set httpOnly session_id JWT cookie and readable csrf_token cookie."""
    session_jwt = create_session_token(user_id)
    csrf_token = secrets.token_urlsafe(32)

    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_jwt,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
        max_age=settings.SESSION_TTL_SECONDS,
        path="/",
    )
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
        max_age=settings.SESSION_TTL_SECONDS,
        path="/",
    )
    return csrf_token


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(key=settings.SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(key=settings.CSRF_COOKIE_NAME, path="/")
