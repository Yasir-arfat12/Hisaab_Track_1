import base64
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.email import Email
from app.models.finance import BankCredit
from app.models.job import Job
from app.models.promise import Promise
from app.models.user import GmailSyncState, OAuthToken, User
from app.services.gmail_service import sync_gmail_for_user
from app.utils.encryption import encrypt_token


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


async def _login_demo(client: AsyncClient) -> str:
    res = await client.post("/api/v1/auth/demo")
    assert res.status_code == 200
    csrf_token = client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert csrf_token is not None
    return csrf_token


async def test_csv_upload_validation_and_list_credits(client: AsyncClient) -> None:
    csrf = await _login_demo(client)

    # Missing required columns -> 422 CREDIT_UPLOAD_FAILED
    bad_csv = b"date,narration\n2026-11-15,FLIPKART\n"
    bad_res = await client.post(
        "/api/v1/credits/upload",
        files={"file": ("bad.csv", bad_csv, "text/csv")},
        data={"bank_name": "HDFC"},
        headers={"X-CSRF-Token": csrf},
    )
    assert bad_res.status_code == 422
    assert bad_res.json()["error"]["code"] == "CREDIT_UPLOAD_FAILED"
    assert "amount" in bad_res.json()["error"]["details"]["missing_columns"]

    # Valid CSV with UTF-8 BOM
    good_csv = (
        "\ufeffdate,description,amount,reference_number\n"
        "2026-11-25,ZOMATO DELIVERY CREDIT,149.00,ZMT998877\n"
    ).encode("utf-8")
    ok_res = await client.post(
        "/api/v1/credits/upload",
        files={"file": ("credits.csv", good_csv, "text/csv")},
        data={"bank_name": "HDFC", "account_last4": "1234"},
        headers={"X-CSRF-Token": csrf},
    )
    assert ok_res.status_code == 200
    upload_data = ok_res.json()["data"]
    assert upload_data["rows_detected"] == 1
    assert upload_data["status"] == "queued"

    list_res = await client.get("/api/v1/credits")
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]["items"]) >= 3


async def test_verify_endpoint_returns_result(client: AsyncClient) -> None:
    csrf = await _login_demo(client)
    promises = (await client.get("/api/v1/promises", params={"status": "pending"})).json()["data"][
        "items"
    ]
    pid = promises[0]["promise_id"]

    res = await client.post(f"/api/v1/verify/{pid}", headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["promise_id"] == pid
    assert data["previous_status"] == "pending"


async def test_gmail_sync_paginated_idempotent_and_purges_bodies(
    db_session: AsyncSession,
) -> None:
    user = User(id=uuid4(), email="syncer@example.com", name="Syncer", is_demo=False)
    db_session.add(user)
    await db_session.flush()

    db_session.add(
        OAuthToken(
            id=uuid4(),
            user_id=user.id,
            provider="google",
            access_token_enc=encrypt_token("valid-access"),
            refresh_token_enc=encrypt_token("valid-refresh"),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            scope="https://www.googleapis.com/auth/gmail.readonly",
        )
    )
    job = Job(id=uuid4(), user_id=user.id, type="gmail_sync", status="pending")
    db_session.add(job)
    await db_session.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/messages"):
            page_token = request.url.params.get("pageToken")
            if not page_token:
                return httpx.Response(
                    200,
                    json={"messages": [{"id": "m1"}], "nextPageToken": "page2"},
                )
            return httpx.Response(200, json={"messages": [{"id": "m2"}]})

        if path.endswith("/messages/m1"):
            return httpx.Response(
                200,
                json={
                    "id": "m1",
                    "threadId": "t1",
                    "internalDate": str(int(datetime(2026, 11, 20, tzinfo=UTC).timestamp() * 1000)),
                    "payload": {
                        "headers": [
                            {"name": "From", "value": "support@flipkart.com"},
                            {"name": "Subject", "value": "Refund initiated"},
                        ],
                        "body": {
                            "data": _b64(
                                "Your Flipkart refund of Rs. 2,499 will be credited by 2026-11-25."
                            )
                        },
                    },
                },
            )
        if path.endswith("/messages/m2"):
            return httpx.Response(
                200,
                json={
                    "id": "m2",
                    "threadId": "t2",
                    "internalDate": str(int(datetime(2026, 11, 22, tzinfo=UTC).timestamp() * 1000)),
                    "payload": {
                        "headers": [
                            {"name": "From", "value": "alerts@hdfcbank.net"},
                            {"name": "Subject", "value": "Credit Alert: Rs. 2,499 credited"},
                        ],
                        "body": {
                            "data": _b64(
                                "Rs. 2,499 credited to your A/c from FLIPKART REF FKT998877."
                            )
                        },
                    },
                },
            )
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        res1 = await sync_gmail_for_user(db_session, user.id, job, http_client=http_client)
        assert res1["emails_scanned"] == 2
        assert res1["promises_extracted"] >= 1
        assert res1["credits_extracted"] == 1

        # Idempotent second run scans 0 new emails
        job2 = Job(id=uuid4(), user_id=user.id, type="gmail_sync", status="pending")
        db_session.add(job2)
        await db_session.commit()
        res2 = await sync_gmail_for_user(db_session, user.id, job2, http_client=http_client)
        assert res2["emails_scanned"] == 0

    emails = (await db_session.execute(select(Email).where(Email.user_id == user.id))).scalars().all()
    assert len(emails) == 2
    assert all(e.body_text is None and e.purged_at is not None for e in emails)

    sync_state = (
        await db_session.execute(select(GmailSyncState).where(GmailSyncState.user_id == user.id))
    ).scalar_one()
    assert sync_state.status == "idle"
    assert sync_state.next_page_token is None

    credits = (
        await db_session.execute(select(BankCredit).where(BankCredit.user_id == user.id))
    ).scalars().all()
    assert len(credits) == 1

    promises = (
        await db_session.execute(select(Promise).where(Promise.user_id == user.id))
    ).scalars().all()
    assert len(promises) >= 1
    assert any(p.status == "kept" for p in promises)
