import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import schemathesis
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.cache import LlmCache
from app.models.promise import Promise
from app.models.user import User
from app.services import dossier_service
from app.services.purge_service import (
    purge_expired_cache_and_idempotency,
    purge_expired_demo_users,
)


async def test_rate_limiting_returns_429_and_retry_after(client: AsyncClient) -> None:
    # POST /api/v1/auth/demo has a 30/hour limit per IP
    for _ in range(30):
        client.cookies.clear()
        res = await client.post("/api/v1/auth/demo")
        assert res.status_code == 200

    client.cookies.clear()
    blocked = await client.post("/api/v1/auth/demo")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"
    assert int(blocked.headers["Retry-After"]) >= 1


async def test_security_headers_and_cors_allow_list(client: AsyncClient) -> None:
    ok_res = await client.get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert ok_res.status_code == 200
    assert ok_res.headers["X-Content-Type-Options"] == "nosniff"
    assert ok_res.headers["X-Frame-Options"] == "DENY"
    assert ok_res.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert ok_res.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"

    blocked_cors = await client.get(
        "/api/v1/health",
        headers={"Origin": "https://evil.example.com"},
    )
    assert blocked_cors.status_code == 200
    assert "Access-Control-Allow-Origin" not in blocked_cors.headers


async def test_purge_service_and_delete_account_cleans_dossiers(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setattr(dossier_service, "DOSSIER_DIR", Path(tmpdir))

        # 1. Demo login + generate a dossier file
        demo_res = await client.post("/api/v1/auth/demo")
        assert demo_res.status_code == 200
        csrf = client.cookies[settings.CSRF_COOKIE_NAME]
        promises = (await client.get("/api/v1/promises")).json()["data"]["items"]
        pid = promises[0]["promise_id"]

        gen_res = await client.post(
            f"/api/v1/dossier/{pid}/generate",
            headers={"X-CSRF-Token": csrf},
        )
        assert gen_res.status_code == 200
        pdf_path = Path(tmpdir) / f"hisaab-dossier-{pid}.pdf"
        assert pdf_path.exists()

        # 2. Delete account removes dossier PDF and user promises
        del_res = await client.delete(
            "/api/v1/auth/me",
            headers={"X-CSRF-Token": csrf},
        )
        assert del_res.status_code == 200
        assert not pdf_path.exists()
        remaining = (
            await db_session.execute(select(Promise).where(Promise.id == UUID(pid)))
        ).scalar_one_or_none()
        assert remaining is None

    # 3. Expired demo user and expired llm_cache purge
    now = datetime.now(UTC)
    old_demo = User(
        id=uuid4(),
        email="old_demo@hisaab.app",
        name="Old Demo",
        is_demo=True,
        created_at=now - timedelta(hours=30),
    )
    fresh_demo = User(
        id=uuid4(),
        email="fresh_demo@hisaab.app",
        name="Fresh Demo",
        is_demo=True,
        created_at=now - timedelta(hours=1),
    )
    expired_cache = LlmCache(
        id=uuid4(),
        prompt_hash="deadbeef" * 8,
        provider="groq",
        model="openai/gpt-oss-120b",
        response_json="{}",
        created_at=now - timedelta(hours=25),
        expires_at=now - timedelta(hours=1),
    )
    db_session.add_all([old_demo, fresh_demo, expired_cache])
    await db_session.commit()

    purged_users = await purge_expired_demo_users(db_session, max_age_hours=24)
    assert purged_users == 1
    purged_cache, _ = await purge_expired_cache_and_idempotency(db_session)
    assert purged_cache == 1


async def test_schemathesis_conformance_against_openapi_yaml(client: AsyncClient) -> None:
    openapi_path = Path(__file__).resolve().parents[3] / "contracts" / "openapi.yaml"
    schema = schemathesis.openapi.from_path(openapi_path)

    # Authenticate via demo mode so protected endpoints can be validated
    demo_res = await client.post("/api/v1/auth/demo")
    assert demo_res.status_code == 200

    endpoints = [
        ("GET", "/health"),
        ("GET", "/auth/me"),
        ("GET", "/gmail/status"),
        ("GET", "/promises"),
        ("GET", "/credits"),
        ("GET", "/dashboard/summary"),
    ]
    for method, path in endpoints:
        operation = schema[path][method.lower()]
        resp = await client.request(method, f"/api/v1{path}")
        assert resp.status_code == 200
        # Validate response status, headers, and JSON body against contracts/openapi.yaml
        operation.validate_response(resp)
