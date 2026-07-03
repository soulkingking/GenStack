import asyncio
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.static import SpaStaticFiles


def _build_app(static_directory: Path) -> FastAPI:
    application = FastAPI()
    application.mount(
        "/", SpaStaticFiles(directory=str(static_directory), html=True), name="static"
    )
    return application


async def _get(application: FastAPI, path: str):
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def test_root_serves_index(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html>genstack-spa</html>", encoding="utf-8")

    response = asyncio.run(_get(_build_app(tmp_path), "/"))

    assert response.status_code == 200
    assert "genstack-spa" in response.text


def test_existing_asset_is_served(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html>genstack-spa</html>", encoding="utf-8")
    (tmp_path / "app.js").write_text("console.info('ok')", encoding="utf-8")

    response = asyncio.run(_get(_build_app(tmp_path), "/app.js"))

    assert response.status_code == 200
    assert "ok" in response.text


def test_deep_link_falls_back_to_index(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html>genstack-spa</html>", encoding="utf-8")

    response = asyncio.run(_get(_build_app(tmp_path), "/dashboard/settings"))

    assert response.status_code == 200
    assert "genstack-spa" in response.text


def test_missing_asset_still_returns_404(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html>genstack-spa</html>", encoding="utf-8")

    response = asyncio.run(_get(_build_app(tmp_path), "/assets/missing.js"))

    assert response.status_code == 404
