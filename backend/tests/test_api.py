import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app


async def _get(path: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def test_health_reports_ok() -> None:
    response = asyncio.run(_get("/api/health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_meta_uses_genstack_identity() -> None:
    response = asyncio.run(_get("/api/meta"))

    assert response.status_code == 200
    assert response.json() == {"name": "GenStack", "version": "0.1.0"}
