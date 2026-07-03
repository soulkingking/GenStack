import asyncio
import sys
import types

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.core import nacos
from app.core.config import Settings


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


class _FakeBuilder:
    """记录链式调用参数的 ClientConfigBuilder 替身。"""

    def __init__(self) -> None:
        self.config: dict[str, str] = {}

    def server_address(self, value: str) -> "_FakeBuilder":
        self.config["server_address"] = value
        return self

    def namespace_id(self, value: str) -> "_FakeBuilder":
        self.config["namespace_id"] = value
        return self

    def username(self, value: str) -> "_FakeBuilder":
        self.config["username"] = value
        return self

    def password(self, value: str) -> "_FakeBuilder":
        self.config["password"] = value
        return self

    def build(self) -> dict[str, str]:
        return self.config


class _FakeParam:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class _FakeNamingService:
    def __init__(self, config) -> None:
        self.config = config
        self.registered: list[_FakeParam] = []
        self.deregistered: list[_FakeParam] = []
        self.shutdown_called = False

    @classmethod
    async def create_naming_service(cls, config) -> "_FakeNamingService":
        return cls(config)

    async def register_instance(self, request: _FakeParam) -> bool:
        self.registered.append(request)
        return True

    async def deregister_instance(self, request: _FakeParam) -> bool:
        self.deregistered.append(request)
        return True

    async def shutdown(self) -> None:
        self.shutdown_called = True


@pytest.fixture
def fake_sdk(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    module = types.ModuleType("v2.nacos")
    module.ClientConfigBuilder = _FakeBuilder
    module.NacosNamingService = _FakeNamingService
    module.RegisterInstanceParam = _FakeParam
    module.DeregisterInstanceParam = _FakeParam
    package = types.ModuleType("v2")
    package.nacos = module
    monkeypatch.setitem(sys.modules, "v2", package)
    monkeypatch.setitem(sys.modules, "v2.nacos", module)
    return module


def test_resolve_instance_ip_prefers_explicit_setting() -> None:
    settings = _settings(nacos_instance_ip="10.1.2.3")

    assert nacos.resolve_instance_ip(settings) == "10.1.2.3"


def test_resolve_instance_ip_probes_local_address() -> None:
    settings = _settings(nacos_server_addr="127.0.0.1:8848")

    assert nacos.resolve_instance_ip(settings) == "127.0.0.1"


def test_register_sends_instance_details(fake_sdk: types.ModuleType) -> None:
    settings = _settings(
        nacos_server_addr="nacos.internal:8848",
        nacos_service_name="genstack-api",
        nacos_username="nacos",
        nacos_password="nacos-pass",
        nacos_instance_ip="10.0.0.5",
    )

    registration = asyncio.run(nacos.register(settings))

    client = registration.client
    assert client.config["server_address"] == "nacos.internal:8848"
    assert client.config["username"] == "nacos"
    assert client.config["password"] == "nacos-pass"
    request = client.registered[0]
    assert request.kwargs["service_name"] == "genstack-api"
    assert request.kwargs["group_name"] == "DEFAULT_GROUP"
    assert request.kwargs["ip"] == "10.0.0.5"
    assert request.kwargs["port"] == 8000
    assert request.kwargs["ephemeral"] is True


def test_deregister_removes_instance_and_closes_client(fake_sdk: types.ModuleType) -> None:
    settings = _settings(nacos_instance_ip="10.0.0.5")
    registration = asyncio.run(nacos.register(settings))

    asyncio.run(nacos.deregister(registration))

    client = registration.client
    assert client.deregistered[0].kwargs["ip"] == "10.0.0.5"
    assert client.deregistered[0].kwargs["port"] == 8000
    assert client.shutdown_called is True


def test_lifespan_skips_registration_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    disabled_settings = main_module.settings.model_copy(update={"nacos_enabled": False})
    monkeypatch.setattr(main_module, "settings", disabled_settings)
    calls: list[Settings] = []

    async def fake_register(settings: Settings):
        calls.append(settings)
        return object()

    monkeypatch.setattr(nacos, "register", fake_register)

    with TestClient(main_module.app):
        pass

    assert calls == []


def test_lifespan_registers_and_deregisters_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enabled_settings = main_module.settings.model_copy(update={"nacos_enabled": True})
    monkeypatch.setattr(main_module, "settings", enabled_settings)
    events: list[tuple[str, object]] = []
    sentinel = object()

    async def fake_register(settings: Settings):
        events.append(("register", settings))
        return sentinel

    async def fake_deregister(registration) -> None:
        events.append(("deregister", registration))

    monkeypatch.setattr(nacos, "register", fake_register)
    monkeypatch.setattr(nacos, "deregister", fake_deregister)

    with TestClient(main_module.app) as client:
        assert events == [("register", enabled_settings)]
        assert client.get("/api/health").status_code == 200

    assert events == [("register", enabled_settings), ("deregister", sentinel)]


def test_startup_survives_registration_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    enabled_settings = main_module.settings.model_copy(update={"nacos_enabled": True})
    monkeypatch.setattr(main_module, "settings", enabled_settings)

    async def fake_register(settings: Settings):
        raise RuntimeError("nacos unreachable")

    monkeypatch.setattr(nacos, "register", fake_register)

    with TestClient(main_module.app) as client:
        assert client.get("/api/health").status_code == 200
