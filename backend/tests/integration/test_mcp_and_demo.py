import json
from uuid import UUID

from fastmcp import Client
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import database, mcp_server
from app.auth.session import create_session_token
from app.config import settings
from app.models.promise import Promise
from app.models.user import User

EXPECTED_MCP_TOOLS = {
    "extract_promises",
    "verify_fulfillment",
    "next_escalation_step",
    "build_dossier",
    "check_merchant_record",
}


async def _login_demo(client: AsyncClient) -> tuple[str, str]:
    res = await client.post("/api/v1/auth/demo")
    assert res.status_code == 200
    csrf = client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert csrf is not None
    return res.json()["data"]["user_id"], csrf


async def test_demo_simulator_all_four_scenarios(client: AsyncClient) -> None:
    _, csrf = await _login_demo(client)

    for scenario in ("refund_arrives", "refund_delayed", "fake_promise", "duplicate_charge"):
        res = await client.post(
            "/api/v1/demo/simulate",
            json={"scenario": scenario},
            headers={"X-CSRF-Token": csrf},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["scenario"] == scenario
        assert "affected_promise_id" in data


async def test_demo_simulator_rejects_non_demo_user(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = User(email="real@example.com", name="Real User", is_demo=False)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_session_token(user.id)
    client.cookies.set(settings.SESSION_COOKIE_NAME, token)
    client.cookies.set(settings.CSRF_COOKIE_NAME, "csrf-123")

    res = await client.post(
        "/api/v1/demo/simulate",
        json={"scenario": "refund_arrives"},
        headers={"X-CSRF-Token": "csrf-123"},
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_mcp_http_mount_requires_token_auth(client: AsyncClient) -> None:
    unauth = await client.post("/mcp/", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert unauth.status_code == 401
    assert unauth.json()["error"]["code"] == "AUTH_REQUIRED"


async def test_mcp_client_lists_five_read_only_tools_and_no_send_tool(
    client: AsyncClient,
    db_session: AsyncSession,
    db_session_factory,
    monkeypatch,
) -> None:
    monkeypatch.setattr(database, "async_session_factory", db_session_factory)
    user_id_str, _ = await _login_demo(client)
    user_id = UUID(user_id_str)

    promises = (
        await db_session.execute(select(Promise).where(Promise.user_id == user_id))
    ).scalars().all()
    assert len(promises) == 8
    target = next(p for p in promises if p.status == "overdue")

    ctx_token = mcp_server.set_mcp_user_id(user_id)
    try:
        async with Client(mcp_server.mcp) as mcp_client:
            tools = await mcp_client.list_tools()
            tool_names = {t.name for t in tools}
            assert tool_names == EXPECTED_MCP_TOOLS

            # Guard test: fail if ANY tool can send or compose mail
            forbidden = ("send", "compose", "mail_send", "gmail_send")
            for tool in tools:
                name_low = tool.name.lower()
                desc_low = (tool.description or "").lower()
                assert not any(word in name_low for word in forbidden), (
                    f"Forbidden send/compose tool found: {tool.name}"
                )
                assert "send email" not in desc_low and "compose" not in desc_low, (
                    f"Tool description implies send/compose capability: {tool.name}"
                )

            # Call all 5 tools via MCP client
            ext_res = await mcp_client.call_tool(
                "extract_promises",
                {"email_text": "Your Flipkart refund of Rs. 2,499 will be credited by 2026-12-10."},
            )
            ext_payload = json.loads(ext_res.content[0].text)
            assert isinstance(ext_payload, list) and len(ext_payload) == 1

            ver_res = await mcp_client.call_tool(
                "verify_fulfillment", {"promise_id": str(target.id)}
            )
            ver_payload = json.loads(ver_res.content[0].text)
            assert ver_payload["promise_id"] == str(target.id)

            esc_res = await mcp_client.call_tool(
                "next_escalation_step", {"promise_id": str(target.id)}
            )
            esc_payload = json.loads(esc_res.content[0].text)
            assert 1 <= esc_payload["next_rung"] <= 4

            dos_res = await mcp_client.call_tool("build_dossier", {"promise_id": str(target.id)})
            dos_payload = json.loads(dos_res.content[0].text)
            assert dos_payload["promise"]["promise_id"] == str(target.id)

            mer_res = await mcp_client.call_tool(
                "check_merchant_record", {"merchant_id": str(target.merchant_id)}
            )
            mer_payload = json.loads(mer_res.content[0].text)
            assert mer_payload["merchant_id"] == str(target.merchant_id)
    finally:
        mcp_server._current_mcp_user_id.reset(ctx_token)
