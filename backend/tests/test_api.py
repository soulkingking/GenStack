import asyncio
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.main import app

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


async def _get(path: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def test_health_reports_ok() -> None:
    response = asyncio.run(_get("/api/health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_meta_uses_app_identity() -> None:
    # 与后端相同的规则读取根目录 VERSION，避免版本升级时测试跟着改。
    expected_version = (
        (_REPOSITORY_ROOT / "VERSION").read_text(encoding="utf-8").strip().splitlines()[0].strip()
    )

    response = asyncio.run(_get("/api/meta"))

    assert response.status_code == 200
    assert response.json() == {"name": "GenStack", "version": expected_version}
