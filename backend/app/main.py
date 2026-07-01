from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import health
from app.core.config import get_settings
from app.core.version import APP_NAME, APP_VERSION

settings = get_settings()

app = FastAPI(title=f"{APP_NAME} API", version=APP_VERSION, debug=settings.app_debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router, prefix="/api")


@app.get("/api/meta")
def meta() -> dict[str, str]:
    """向前端暴露不含敏感信息的应用名称与版本。"""

    return {"name": APP_NAME, "version": APP_VERSION}


_repository_root = Path(__file__).resolve().parents[2]
_static_directory = _repository_root / "static"
# 前端产物只存在于生产镜像；本地使用 Vite 时不能占用 FastAPI 根路径。
if _static_directory.is_dir():
    app.mount("/", StaticFiles(directory=str(_static_directory), html=True), name="static")
