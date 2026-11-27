import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import status

from app.config import settings
from app.utils.exceptions import AppError, ErrorCode

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GMAIL_READONLY_SCOPE = "openid email profile https://www.googleapis.com/auth/gmail.readonly"


def create_oauth_state() -> str:
    """Create a short-lived signed state token for anti-CSRF protection."""
    now = datetime.now(UTC)
    payload = {
        "nonce": secrets.token_urlsafe(16),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY.get_secret_value(), algorithm="HS256")


def verify_oauth_state(state: str, cookie_state: str | None) -> None:
    """Verify signed OAuth state token and optional cookie match."""
    if not state or (cookie_state is not None and state != cookie_state):
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid or expired state token",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"field": "state"},
        )
    try:
        jwt.decode(state, settings.SECRET_KEY.get_secret_value(), algorithms=["HS256"])
    except jwt.InvalidTokenError as exc:
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid or expired state token",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"field": "state"},
        ) from exc


def build_google_auth_url(state: str) -> str:
    if not settings.GOOGLE_CLIENT_ID:
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message="OAuth configuration missing",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": GMAIL_READONLY_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(
    code: str,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET.get_secret_value(),
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    if http_client is not None:
        resp = await http_client.post(GOOGLE_TOKEN_URL, data=data, timeout=15.0)
    else:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(GOOGLE_TOKEN_URL, data=data)

    if resp.status_code != 200:
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Failed to exchange Google authorization code",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"field": "code"},
        )
    return dict(resp.json())


async def fetch_google_userinfo(
    access_token: str,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    if http_client is not None:
        resp = await http_client.get(GOOGLE_USERINFO_URL, headers=headers, timeout=15.0)
    else:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(GOOGLE_USERINFO_URL, headers=headers)

    if resp.status_code != 200:
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Failed to fetch Google user profile",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return dict(resp.json())


async def revoke_google_token(
    token: str,
    http_client: httpx.AsyncClient | None = None,
) -> None:
    """Best-effort Google token revocation."""
    try:
        if http_client is not None:
            await http_client.post(GOOGLE_REVOKE_URL, params={"token": token}, timeout=10.0)
        else:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(GOOGLE_REVOKE_URL, params={"token": token})
    except httpx.HTTPError:
        return
