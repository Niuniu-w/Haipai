import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_health_check() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_health_check_allows_local_frontend_origin() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/health",
            headers={"Origin": "http://127.0.0.1:4174"},
        )

        assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:4174"


@pytest.mark.anyio
async def test_ai_status_does_not_expose_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORYFORGE_LLM_API_KEY", "secret-test-key")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/ai/status")

        assert response.status_code == 200
        assert response.json()["configured"] is True
        assert "key" not in response.text.lower()
