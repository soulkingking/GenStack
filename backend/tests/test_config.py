import pytest

from app.core.config import Settings


def _settings(**overrides) -> Settings:
    # 关闭 .env 读取，让用例只受显式参数和进程环境变量影响。
    return Settings(_env_file=None, **overrides)


def test_defaults_keep_oauth_and_nacos_safe_for_local_development() -> None:
    settings = _settings()

    assert settings.oauth2_scope == ""
    assert settings.oauth2_state_ttl_seconds == 300
    assert settings.oauth2_default_session_ttl_seconds == 3600
    assert settings.auth_cookie_secure is False
    assert settings.oauth2_configured is False
    assert settings.nacos_enabled is False
    assert settings.nacos_server_addr == "127.0.0.1:8848"
    assert settings.nacos_group == "DEFAULT_GROUP"
    assert settings.nacos_service_name == "genstack"
    assert settings.nacos_instance_port == 8000


def test_environment_overrides_oauth_and_nacos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OAUTH2_AUTHORIZE_URL", "https://auth.example/oauth2/authorize")
    monkeypatch.setenv("OAUTH2_TOKEN_URL", "https://auth.example/oauth2/token")
    monkeypatch.setenv("OAUTH2_CLIENT_ID", "genstack-client")
    monkeypatch.setenv("OAUTH2_CLIENT_SECRET", "server-secret")
    monkeypatch.setenv("OAUTH2_REDIRECT_URI", "https://app.example/")
    monkeypatch.setenv("OAUTH2_SCOPE", "all")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("NACOS_ENABLED", "true")
    monkeypatch.setenv("NACOS_SERVER_ADDR", "nacos.internal:8848")
    monkeypatch.setenv("NACOS_SERVICE_NAME", "genstack-api")

    settings = _settings()

    assert settings.oauth2_authorize_url == "https://auth.example/oauth2/authorize"
    assert settings.oauth2_token_url == "https://auth.example/oauth2/token"
    assert settings.oauth2_client_id == "genstack-client"
    assert settings.oauth2_client_secret.get_secret_value() == "server-secret"
    assert settings.oauth2_redirect_uri == "https://app.example/"
    assert settings.oauth2_scope == "all"
    assert settings.auth_cookie_secure is True
    assert settings.oauth2_configured is True
    assert settings.nacos_enabled is True
    assert settings.nacos_server_addr == "nacos.internal:8848"
    assert settings.nacos_service_name == "genstack-api"


def test_oauth_configuration_requires_every_server_side_value() -> None:
    settings = _settings(
        oauth2_authorize_url="https://auth.example/oauth2/authorize",
        oauth2_token_url="https://auth.example/oauth2/token",
        oauth2_client_id="genstack-client",
        oauth2_client_secret="",
        oauth2_redirect_uri="https://app.example/",
    )

    assert settings.oauth2_configured is False
