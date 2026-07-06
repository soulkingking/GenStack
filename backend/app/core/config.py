from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
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

    # 第三方登录总开关：默认关闭，关闭时页面匿名访问、登录相关接口不可用。
    auth_enabled: bool = False

    # OAuth2 客户端密钥只在后端使用；SecretStr 避免配置对象日志意外输出明文。
    oauth2_authorize_url: str = ""
    oauth2_token_url: str = ""
    oauth2_userinfo_url: str = ""
    oauth2_client_id: str = ""
    oauth2_client_secret: SecretStr = SecretStr("")
    oauth2_redirect_uri: str = ""
    oauth2_scope: str = ""
    oauth2_state_ttl_seconds: int = Field(default=300, gt=0)
    oauth2_default_session_ttl_seconds: int = Field(default=3600, gt=0)
    auth_cookie_secure: bool = False

    # Nacos 服务注册：默认关闭；启用后应用启动时注册实例、关闭时注销。
    nacos_enabled: bool = False
    nacos_server_addr: str = "127.0.0.1:8848"
    nacos_namespace: str = ""
    nacos_group: str = "DEFAULT_GROUP"
    nacos_service_name: str = "genstack"
    nacos_username: str = ""
    nacos_password: str = ""
    # 实例注册地址：IP 留空时自动探测本机对外地址。
    nacos_instance_ip: str = ""
    nacos_instance_port: int = 8000

    @property
    def cors_origin_list(self) -> list[str]:
        """返回供 CORS 中间件使用的已清理非空来源列表。"""

        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def oauth2_configured(self) -> bool:
        """返回第三方登录所需服务端配置是否完整。"""

        return all(
            value.strip()
            for value in (
                self.oauth2_authorize_url,
                self.oauth2_token_url,
                self.oauth2_client_id,
                self.oauth2_client_secret.get_secret_value(),
                self.oauth2_redirect_uri,
            )
        )


@lru_cache
def get_settings() -> Settings:
    """返回进程内复用的不可变配置实例。"""

    return Settings()
