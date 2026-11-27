from datetime import date, timedelta

from httpx import AsyncClient

from app.config import settings


async def _login_demo(client: AsyncClient) -> str:
    res = await client.post("/api/v1/auth/demo")
    assert res.status_code == 200
    csrf_token = client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert csrf_token is not None
    return csrf_token


async def test_dashboard_summary_matches_demo_seed(client: AsyncClient) -> None:
    await _login_demo(client)

    res = await client.get("/api/v1/dashboard/summary")
    assert res.status_code == 200
    body = res.json()
    assert body["error"] is None
    data = body["data"]

    assert data["counts"] == {
        "total": 8,
        "pending": 1,
        "kept": 2,
        "overdue": 2,
        "needs_review": 2,
        "dismissed": 1,
    }
    assert data["total_kept_paise"] == 249900 + 89900
    assert data["total_overdue_paise"] == 1500000 + 65000
    assert data["total_owed_paise"] == 1500000 + 14900 + 320000 + 65000 + 9999900


async def test_promise_list_filters(client: AsyncClient) -> None:
    await _login_demo(client)

    overdue_res = await client.get("/api/v1/promises", params={"status": "overdue"})
    assert overdue_res.status_code == 200
    overdue_items = overdue_res.json()["data"]["items"]
    assert len(overdue_items) == 2
    assert {item["merchant_name"] for item in overdue_items} == {"HDFC Insurance", "BookMyShow"}

    cat_res = await client.get("/api/v1/promises", params={"category": "ticket"})
    assert cat_res.status_code == 200
    cat_items = cat_res.json()["data"]["items"]
    assert len(cat_items) == 2
    assert {item["merchant_name"] for item in cat_items} == {"IRCTC", "BookMyShow"}

    flipkart_id = (
        await client.get("/api/v1/promises", params={"status": "kept"})
    ).json()["data"]["items"][0]["merchant_id"]
    merch_res = await client.get("/api/v1/promises", params={"merchant_id": flipkart_id})
    assert merch_res.status_code == 200
    assert len(merch_res.json()["data"]["items"]) == 1

    today = date.today()
    future_res = await client.get(
        "/api/v1/promises",
        params={"date_from": (today + timedelta(days=1)).isoformat()},
    )
    assert future_res.status_code == 200
    future_items = future_res.json()["data"]["items"]
    assert {item["merchant_name"] for item in future_items} == {"Zomato", "Unknown Merchant"}


async def test_promise_list_cursor_pagination(client: AsyncClient) -> None:
    await _login_demo(client)

    seen_ids: list[str] = []
    cursor: str | None = None
    pages = 0

    while True:
        params: dict[str, str | int] = {"limit": 3}
        if cursor is not None:
            params["cursor"] = cursor
        res = await client.get("/api/v1/promises", params=params)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["limit"] == 3
        seen_ids.extend(item["promise_id"] for item in data["items"])
        pages += 1
        cursor = data["next_cursor"]
        if cursor is None:
            break

    assert pages == 3
    assert len(seen_ids) == 8
    assert len(set(seen_ids)) == 8

    bad_cursor = await client.get("/api/v1/promises", params={"cursor": "not-valid-base64"})
    assert bad_cursor.status_code == 422
    assert bad_cursor.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_promise_detail_and_patch(client: AsyncClient) -> None:
    csrf_token = await _login_demo(client)

    overdue_items = (
        await client.get("/api/v1/promises", params={"status": "overdue"})
    ).json()["data"]["items"]
    hdfc = next(i for i in overdue_items if i["merchant_name"] == "HDFC Insurance")

    detail_res = await client.get(f"/api/v1/promises/{hdfc['promise_id']}")
    assert detail_res.status_code == 200
    detail = detail_res.json()["data"]
    assert detail["merchant_name"] == "HDFC Insurance"
    assert detail["escalation_rung"] == 2
    assert detail["source_email_subject"] == "Your claim #CLM-2026-4521 has been approved"
    assert detail["confidence"] == 0.97
    assert detail["extraction_method"] == "llm"
    assert "exact_quote" in detail
    assert len(detail["timeline"]) >= 3

    pending_items = (
        await client.get("/api/v1/promises", params={"status": "pending"})
    ).json()["data"]["items"]
    zomato_id = pending_items[0]["promise_id"]

    # Reject non-dismissed status updates
    bad_patch = await client.patch(
        f"/api/v1/promises/{zomato_id}",
        json={"status": "kept"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert bad_patch.status_code == 422
    assert bad_patch.json()["error"]["code"] == "VALIDATION_ERROR"

    patch_res = await client.patch(
        f"/api/v1/promises/{zomato_id}",
        json={"status": "dismissed", "user_note": "Resolved directly"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["status"] == "dismissed"


async def test_promise_ownership_isolation(client: AsyncClient) -> None:
    # User A logs in and gets a promise ID
    await _login_demo(client)
    user_a_promises = (await client.get("/api/v1/promises")).json()["data"]["items"]
    user_a_promise_id = user_a_promises[0]["promise_id"]

    # User B logs in as a separate demo user (clear User A cookies first)
    client.cookies.clear()
    csrf_b = await _login_demo(client)

    get_res = await client.get(f"/api/v1/promises/{user_a_promise_id}")
    assert get_res.status_code == 404
    assert get_res.json()["error"]["code"] == "PROMISE_NOT_FOUND"

    patch_res = await client.patch(
        f"/api/v1/promises/{user_a_promise_id}",
        json={"user_note": "Unauthorized edit"},
        headers={"X-CSRF-Token": csrf_b},
    )
    assert patch_res.status_code == 404
    assert patch_res.json()["error"]["code"] == "PROMISE_NOT_FOUND"
