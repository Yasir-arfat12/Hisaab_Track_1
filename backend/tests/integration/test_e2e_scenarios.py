from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import schemathesis
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.llm.providers.openai_compat import ProviderSpec
from app.llm.router import LLMRouter
from app.schemas.escalation import EscalationDraftRequest
from app.services.escalation_service import generate_escalation_draft
from app.services.extraction_service import extract_promises


async def test_e2e_seven_integration_scenarios_and_schemathesis(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    # (1) Demo login -> dashboard
    demo_res = await client.post("/api/v1/auth/demo")
    assert demo_res.status_code == 200
    csrf = client.cookies[settings.CSRF_COOKIE_NAME]

    dash_res = await client.get("/api/v1/dashboard/summary")
    assert dash_res.status_code == 200
    assert dash_res.json()["data"]["counts"]["total"] == 8

    # (2) Refund Arrives flips a pending promise to kept
    pending = (
        await client.get("/api/v1/promises", params={"status": "pending"})
    ).json()["data"]["items"][0]
    arrives_res = await client.post(
        "/api/v1/demo/simulate",
        json={"scenario": "refund_arrives", "promise_id": pending["promise_id"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert arrives_res.status_code == 200
    kept_detail = (
        await client.get(f"/api/v1/promises/{pending['promise_id']}")
    ).json()["data"]
    assert kept_detail["status"] == "kept"

    # (3) Refund Delayed reaches the next escalation rung on the right date
    overdue_items = (
        await client.get("/api/v1/promises", params={"status": "overdue"})
    ).json()["data"]["items"]
    overdue_id = overdue_items[0]["promise_id"]
    delayed_res = await client.post(
        "/api/v1/demo/simulate",
        json={"scenario": "refund_delayed", "promise_id": overdue_id},
        headers={"X-CSRF-Token": csrf},
    )
    assert delayed_res.status_code == 200
    next_step = (
        await client.get(f"/api/v1/escalation/{overdue_id}/next-step")
    ).json()["data"]
    assert next_step["next_rung"] >= 2

    # (4) Fake Promise Email is flagged needs_review and triggers no action
    fake_res = await client.post(
        "/api/v1/demo/simulate",
        json={"scenario": "fake_promise"},
        headers={"X-CSRF-Token": csrf},
    )
    assert fake_res.status_code == 200
    fake_id = fake_res.json()["data"]["affected_promise_id"]
    fake_detail = (await client.get(f"/api/v1/promises/{fake_id}")).json()["data"]
    assert fake_detail["status"] == "needs_review"
    assert fake_detail["confidence"] == 0.0
    assert "injection" in (fake_detail["needs_review_reason"] or "").lower()

    # (5) Duplicate Charge scenario runs
    dup_res = await client.post(
        "/api/v1/demo/simulate",
        json={"scenario": "duplicate_charge"},
        headers={"X-CSRF-Token": csrf},
    )
    assert dup_res.status_code == 200

    # (6) Every LLM provider down -> deterministic fallback extraction + template draft
    no_keys_router = LLMRouter(
        specs=[
            ProviderSpec(
                spec_id="groq:disabled",
                provider="groq",
                model="disabled",
                base_url="https://invalid.local",
                api_key="",
            )
        ]
    )
    fallback_candidates = await extract_promises(
        "Your Flipkart refund of Rs. 1,299 will be credited by 2026-12-15.",
        sender="support@flipkart.com",
        received_at=datetime(2026, 11, 26, tzinfo=UTC),
        db=db_session,
        router=no_keys_router,
    )
    assert len(fallback_candidates) == 1
    assert fallback_candidates[0].extraction_method == "deterministic"

    draft = await generate_escalation_draft(
        db_session,
        UUID(demo_res.json()["data"]["user_id"]),
        UUID(overdue_id),
        EscalationDraftRequest(rung=2, tone="firm", include_legal_references=True),
        router=no_keys_router,
    )
    assert draft.model_used == "deterministic-template"
    assert settings.NOT_LEGAL_ADVICE_TEXT in draft.not_legal_advice_notice

    # (7) Gmail token revoked/missing -> GMAIL_AUTH_EXPIRED (401) + status connected=false
    gmail_status = (await client.get("/api/v1/gmail/status")).json()["data"]
    assert gmail_status["connected"] is False
    sync_res = await client.post("/api/v1/gmail/sync", headers={"X-CSRF-Token": csrf})
    assert sync_res.status_code == 401
    assert sync_res.json()["error"]["code"] == "GMAIL_AUTH_EXPIRED"

    # Schemathesis conformance against contracts/openapi.yaml
    openapi_path = Path(__file__).resolve().parents[3] / "contracts" / "openapi.yaml"
    schema = schemathesis.openapi.from_path(openapi_path)
    for method, schema_path, req_path in [
        ("GET", "/health", "/health"),
        ("GET", "/auth/me", "/auth/me"),
        ("GET", "/gmail/status", "/gmail/status"),
        ("GET", "/promises", "/promises"),
        ("GET", "/promises/{promise_id}", f"/promises/{overdue_id}"),
        ("GET", "/credits", "/credits"),
        ("GET", "/dashboard/summary", "/dashboard/summary"),
        ("GET", "/escalation/{promise_id}/next-step", f"/escalation/{overdue_id}/next-step"),
    ]:
        op = schema[schema_path][method.lower()]
        resp = await client.request(method, f"/api/v1{req_path}")
        assert resp.status_code == 200
        op.validate_response(resp)
