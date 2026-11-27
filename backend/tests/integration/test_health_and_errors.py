from fastapi import FastAPI
from httpx import AsyncClient

from app.utils.exceptions import AppError, ErrorCode


async def test_health_endpoint_returns_standard_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    body = response.json()
    assert body["error"] is None
    data = body["data"]
    assert data["status"] in ("ok", "degraded")
    assert data["version"] == "1.0.0"
    assert data["checks"]["database"] == "ok"
    assert data["checks"]["llm"] in ("ok", "degraded", "error")
    assert "redis" not in data["checks"]
    assert isinstance(data["uptime_seconds"], int)


async def test_request_id_header_is_preserved(client: AsyncClient) -> None:
    custom_id = "req-12345-abcde"
    response = await client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id


async def test_not_found_returns_standard_error_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == ErrorCode.NOT_FOUND


async def test_app_error_returns_contract_error_code(
    test_app: FastAPI, client: AsyncClient
) -> None:
    @test_app.get("/api/v1/_test/promise-error")
    async def _raise_promise_error() -> None:
        raise AppError(
            code=ErrorCode.PROMISE_NOT_FOUND,
            message="Promise not found",
            status_code=404,
            details={"promise_id": "11111111-0001-0000-0000-000000000001"},
        )

    response = await client.get("/api/v1/_test/promise-error")
    assert response.status_code == 404
    body = response.json()
    assert body == {
        "data": None,
        "error": {
            "code": "PROMISE_NOT_FOUND",
            "message": "Promise not found",
            "details": {"promise_id": "11111111-0001-0000-0000-000000000001"},
        },
    }
