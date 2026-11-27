from unittest.mock import AsyncMock

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.promise import Promise
from app.models.user import OAuthToken
from app.routers import auth as auth_router
from app.utils.encryption import decrypt_token, encrypt_token


def test_fernet_encrypt_decrypt_roundtrip() -> None:
    secret = "test-secret-key"
    plaintext = "ya29.a0AfH6SMB_mock_google_token"
    encrypted = encrypt_token(plaintext, secret=secret)
    assert encrypted != plaintext
    assert decrypt_token(encrypted, secret=secret) == plaintext


async def test_auth_required_without_session(client: AsyncClient) -> None:
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTH_REQUIRED"

    logout_res = await client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 401
    assert logout_res.json()["error"]["code"] == "AUTH_REQUIRED"


async def test_google_oauth_start_and_callback_with_mocked_google(
    client: AsyncClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "mock-client-id")
    monkeypatch.setattr(
        auth_router,
        "exchange_code_for_tokens",
        AsyncMock(
            return_value={
                "access_token": "mock-access-token-123",
                "refresh_token": "mock-refresh-token-456",
                "expires_in": 3600,
                "scope": "openid email profile https://www.googleapis.com/auth/gmail.readonly",
            }
        ),
    )
    monkeypatch.setattr(
        auth_router,
        "fetch_google_userinfo",
        AsyncMock(
            return_value={
                "email": "rahul@example.com",
                "name": "Rahul Sharma",
                "picture": "https://example.com/avatar.png",
            }
        ),
    )

    start_res = await client.get("/api/v1/auth/google/start")
    assert start_res.status_code == 200
    redirect_url = start_res.json()["data"]["redirect_url"]
    assert "accounts.google.com" in redirect_url
    assert "gmail.readonly" in redirect_url

    state_cookie = start_res.cookies.get("oauth_state")
    assert state_cookie is not None

    bad_cb = await client.get(
        "/api/v1/auth/google/callback",
        params={"code": "auth-code", "state": "wrong-state"},
    )
    assert bad_cb.status_code == 422
    assert bad_cb.json()["error"]["code"] == "VALIDATION_ERROR"

    cb_res = await client.get(
        "/api/v1/auth/google/callback",
        params={"code": "auth-code", "state": state_cookie},
    )
    assert cb_res.status_code == 200
    body = cb_res.json()["data"]
    assert body["email"] == "rahul@example.com"
    assert body["display_name"] == "Rahul Sharma"
    assert settings.SESSION_COOKIE_NAME in cb_res.cookies
    assert settings.CSRF_COOKIE_NAME in cb_res.cookies

    me_res = await client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["data"]["gmail_connected"] is True
    assert me_res.json()["data"]["is_demo"] is False


async def test_google_tokens_are_stored_encrypted(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "mock-client-id")
    monkeypatch.setattr(
        auth_router,
        "exchange_code_for_tokens",
        AsyncMock(
            return_value={
                "access_token": "plain-access-secret",
                "refresh_token": "plain-refresh-secret",
                "expires_in": 3600,
            }
        ),
    )
    monkeypatch.setattr(
        auth_router,
        "fetch_google_userinfo",
        AsyncMock(return_value={"email": "enc@example.com", "name": "Enc User"}),
    )

    start_res = await client.get("/api/v1/auth/google/start")
    state = start_res.cookies["oauth_state"]
    cb_res = await client.get(
        "/api/v1/auth/google/callback",
        params={"code": "code-1", "state": state},
    )
    assert cb_res.status_code == 200

    tok = (await db_session.execute(select(OAuthToken))).scalar_one()
    assert tok.access_token_enc != "plain-access-secret"
    assert tok.refresh_token_enc != "plain-refresh-secret"
    assert decrypt_token(tok.access_token_enc) == "plain-access-secret"
    assert decrypt_token(tok.refresh_token_enc) == "plain-refresh-secret"


async def test_demo_login_csrf_logout_and_delete(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    demo_res = await client.post("/api/v1/auth/demo")
    assert demo_res.status_code == 200
    demo_data = demo_res.json()["data"]
    assert demo_data["is_demo"] is True
    assert demo_data["seed_scenario"] == "v1_standard_8_promises"

    promises = (await db_session.execute(select(Promise))).scalars().all()
    assert len(promises) == 8

    me_res = await client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["data"]["is_demo"] is True

    # Authenticated POST without X-CSRF-Token must be blocked
    csrf_fail = await client.post("/api/v1/auth/logout")
    assert csrf_fail.status_code == 403
    assert csrf_fail.json()["error"]["code"] == "VALIDATION_ERROR"

    csrf_token = client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert csrf_token is not None

    # Authenticated DELETE /auth/me with valid CSRF token succeeds
    monkeypatch.setattr(auth_router, "revoke_google_token", AsyncMock())
    del_res = await client.delete(
        "/api/v1/auth/me",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert del_res.status_code == 200
    assert del_res.json()["data"] == {"deleted": True}

    after_del = await client.get("/api/v1/auth/me")
    assert after_del.status_code == 401
    assert after_del.json()["error"]["code"] == "AUTH_REQUIRED"


async def test_logout_clears_session_cookie(client: AsyncClient) -> None:
    demo_res = await client.post("/api/v1/auth/demo")
    assert demo_res.status_code == 200

    csrf_token = client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert csrf_token is not None

    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["data"] == {"logged_out": True}

    me_res = await client.get("/api/v1/auth/me")
    assert me_res.status_code == 401
    assert me_res.json()["error"]["code"] == "AUTH_REQUIRED"
