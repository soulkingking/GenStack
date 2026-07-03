import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.core import nacos
from app.core.config import get_settings
from app.core.static import SpaStaticFiles
from app.core.version import APP_NAME, APP_VERSION

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    registration = None
    if settings.nacos_enabled:
        # 注册失败只记录日志：服务发现不可用不应阻止应用本身对外提供服务。
        try:
            registration = await nacos.register(settings)
        except Exception:
            logger.exception("Nacos 服务注册失败，应用继续启动")
    yield
    if registration is not None:
        try:
            await nacos.deregister(registration)
        except Exception:
            logger.exception("Nacos 服务注销失败")


app = FastAPI(
    title=f"{APP_NAME} API",
    version=APP_VERSION,
    debug=settings.app_debug,
    lifespan=lifespan,
)
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
    app.mount("/", SpaStaticFiles(directory=str(_static_directory), html=True), name="static")
