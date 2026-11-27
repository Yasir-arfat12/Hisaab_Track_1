import tempfile
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.promise import Merchant, Promise
from app.models.user import User
from app.services import dossier_service
from app.services.escalation_service import (
    compute_rung_for_days_overdue,
    get_next_escalation_step,
)


async def _login_demo(client: AsyncClient) -> str:
    res = await client.post("/api/v1/auth/demo")
    assert res.status_code == 200
    csrf_token = client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert csrf_token is not None
    return csrf_token


@pytest.mark.parametrize(
    ("days_overdue", "expected_rung"),
    [
        (0, 1),
        (7, 1),
        (8, 2),
        (21, 2),
        (22, 3),
        (45, 3),
        (46, 4),
        (100, 4),
    ],
)
async def test_escalation_rung_boundaries_on_ist_dates(
    db_session: AsyncSession,
    days_overdue: int,
    expected_rung: int,
) -> None:
    assert compute_rung_for_days_overdue(days_overdue) == expected_rung

    user = User(
        id=uuid4(),
        email=f"ist_{days_overdue}@example.com",
        name="IST User",
        is_demo=False,
    )
    merchant = Merchant(
        id=uuid4(),
        name="Flipkart",
        normalized_name=f"flipkart_ist_{days_overdue}",
    )
    db_session.add_all([user, merchant])
    await db_session.flush()

    due_date_ist = date(2026, 11, 1)
    today_ist = due_date_ist + timedelta(days=days_overdue)

    promise = Promise(
        id=uuid4(),
        user_id=user.id,
        merchant_id=merchant.id,
        merchant_name="Flipkart",
        category="refund",
        amount_paise=249900,
        due_date=due_date_ist,
        exact_quote="Your Flipkart refund of Rs. 2,499 will be credited.",
        confidence=0.95,
        status="overdue",
        extraction_method="llm",
    )
    db_session.add(promise)
    await db_session.commit()

    step = await get_next_escalation_step(
        db_session, user.id, promise.id, today_ist=today_ist
    )
    assert step.next_rung == expected_rung


def test_configurable_escalation_thresholds() -> None:
    custom = [3, 10, 20]
    assert compute_rung_for_days_overdue(3, custom) == 1
    assert compute_rung_for_days_overdue(4, custom) == 2
    assert compute_rung_for_days_overdue(11, custom) == 3
    assert compute_rung_for_days_overdue(21, custom) == 4


async def test_escalation_endpoints_and_template_fallback(client: AsyncClient) -> None:
    csrf = await _login_demo(client)
    promises = (
        await client.get("/api/v1/promises", params={"status": "overdue"})
    ).json()["data"]["items"]
    hdfc_id = next(p["promise_id"] for p in promises if p["merchant_name"] == "HDFC Insurance")

    next_res = await client.get(f"/api/v1/escalation/{hdfc_id}/next-step")
    assert next_res.status_code == 200
    next_data = next_res.json()["data"]
    assert 1 <= next_data["next_rung"] <= 4
    assert "deadline_date" in next_data

    draft_res = await client.post(
        f"/api/v1/escalation/{hdfc_id}/draft",
        json={"rung": 2, "tone": "firm", "include_legal_references": True},
        headers={"X-CSRF-Token": csrf},
    )
    assert draft_res.status_code == 200
    draft_data = draft_res.json()["data"]
    assert draft_data["rung"] == 2
    assert "HDFC Insurance" in draft_data["draft_text"]
    assert draft_data["not_legal_advice_notice"] == settings.NOT_LEGAL_ADVICE_TEXT
    assert draft_data["model_used"] == "deterministic-template"


async def test_dossier_generate_and_download_pdf(
    client: AsyncClient,
    monkeypatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setattr(dossier_service, "DOSSIER_DIR", Path(tmpdir))
        csrf = await _login_demo(client)
        promises = (await client.get("/api/v1/promises")).json()["data"]["items"]
        pid = promises[0]["promise_id"]

        # Download before generation -> 500 DOSSIER_GENERATION_FAILED
        missing_dl = await client.get(f"/api/v1/dossier/{pid}/download")
        assert missing_dl.status_code == 500
        assert missing_dl.json()["error"]["code"] == "DOSSIER_GENERATION_FAILED"

        gen_res = await client.post(
            f"/api/v1/dossier/{pid}/generate",
            headers={"X-CSRF-Token": csrf},
        )
        assert gen_res.status_code == 200
        assert gen_res.json()["data"]["status"] == "queued"

        dl_res = await client.get(f"/api/v1/dossier/{pid}/download")
        assert dl_res.status_code == 200
        assert dl_res.headers["content-type"] == "application/pdf"
        assert f"hisaab-dossier-{pid}.pdf" in dl_res.headers["content-disposition"]
        assert dl_res.content.startswith(b"%PDF-")


async def test_merchant_record_endpoint(client: AsyncClient) -> None:
    await _login_demo(client)
    kept_items = (
        await client.get("/api/v1/promises", params={"status": "kept"})
    ).json()["data"]["items"]
    flipkart_id = next(
        p["merchant_id"] for p in kept_items if p["merchant_name"] == "Flipkart"
    )

    res = await client.get(f"/api/v1/merchants/{flipkart_id}/record")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["merchant_name"] == "Flipkart"
    assert data["total_promises"] == 1
    assert data["kept_count"] == 1
    assert data["keep_rate_pct"] == 100.0

    not_found = await client.get(f"/api/v1/merchants/{uuid4()}/record")
    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "NOT_FOUND"
