import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_returns_ok_with_db_status(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert "db" in body
    assert body["db"] in ("ok", "error")


@pytest.mark.asyncio
async def test_health_includes_version(client: AsyncClient):
    resp = await client.get("/health")
    body = resp.json()
    assert "version" in body
    assert body["version"] == "0.1.0"
