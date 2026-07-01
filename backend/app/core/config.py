from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 始终从仓库根目录读取 .env 和 data，使本地运行与容器目录约定保持一致。
_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_SQLITE_URL = f"sqlite:///{(_REPOSITORY_ROOT / 'data' / 'app.db').as_posix()}"


class Settings(BaseSettings):
    """从进程环境变量和仓库根目录 .env 加载运行时配置。"""

    model_config = SettingsConfigDict(
        env_file=str(_REPOSITORY_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    app_debug: bool = False
    database_url: str = _DEFAULT_SQLITE_URL
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        """返回供 CORS 中间件使用的已清理非空来源列表。"""

        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """返回进程内复用的不可变配置实例。"""

    return Settings()
