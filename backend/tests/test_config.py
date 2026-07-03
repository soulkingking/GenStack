import pytest

from app.core.config import Settings


def _settings(**overrides) -> Settings:
    # 关闭 .env 读取，让用例只受显式参数和进程环境变量影响。
    return Settings(_env_file=None, **overrides)


def test_defaults_keep_auth_and_nacos_reserved() -> None:
    settings = _settings()

    assert settings.auth_username == "admin"
    assert settings.auth_password == "admin"
    assert settings.nacos_enabled is False
    assert settings.nacos_server_addr == "127.0.0.1:8848"
    assert settings.nacos_group == "DEFAULT_GROUP"
    assert settings.nacos_service_name == "genstack"
    assert settings.nacos_instance_port == 8000


def test_environment_overrides_auth_and_nacos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_USERNAME", "ops")
    monkeypatch.setenv("AUTH_PASSWORD", "s3cret")
    monkeypatch.setenv("NACOS_ENABLED", "true")
    monkeypatch.setenv("NACOS_SERVER_ADDR", "nacos.internal:8848")
    monkeypatch.setenv("NACOS_SERVICE_NAME", "genstack-api")

    settings = _settings()

    assert settings.auth_username == "ops"
    assert settings.auth_password == "s3cret"
    assert settings.nacos_enabled is True
    assert settings.nacos_server_addr == "nacos.internal:8848"
    assert settings.nacos_service_name == "genstack-api"
