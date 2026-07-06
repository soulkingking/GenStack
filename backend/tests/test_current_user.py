import asyncio

import httpx
from fastapi import FastAPI

from app.api import current_user
from app.clients.base import RemoteAuthenticationError, RemoteServiceError
from app.clients.user import CurrentUser
from app.core.config import Settings

_SETTINGS = Settings(
    _env_file=None,
    oauth2_userinfo_url="https://auth.example/oauth2/userinfo",
)


class FakeUserClient:
    def __init__(
        self,
        *,
        result: CurrentUser | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or CurrentUser(username="admin")
        self.error = error
        self.calls: list[str] = []

    async def get_current_user(self, access_token: str) -> CurrentUser:
        self.calls.append(access_token)
        if self.error is not None:
            raise self.error
        return self.result


async def _request(
    *,
    user_client: FakeUserClient,
    settings: Settings = _SETTINGS,
    cookies: dict[str, str] | None = None,
) -> httpx.Response:
    app = FastAPI()
    app.include_router(current_user.router, prefix="/api")
    app.dependency_overrides[current_user.get_current_user_settings] = lambda: settings
    app.dependency_overrides[current_user.get_user_client] = lambda: user_client

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies=cookies,
    ) as client:
        return await client.get("/api/current-user")


def test_current_user_rejects_missing_cookie_without_remote_call() -> None:
    user_client = FakeUserClient()

    response = asyncio.run(_request(user_client=user_client))

    assert response.status_code == 401
    assert response.json() == {"detail": "未登录"}
    assert user_client.calls == []


def test_current_user_rejects_blank_cookie_without_remote_call() -> None:
    user_client = FakeUserClient()

    response = asyncio.run(
        _request(
            user_client=user_client,
            cookies={"genstack_session": "   "},
        )
    )

    assert response.status_code == 401
    assert user_client.calls == []


def test_current_user_returns_only_local_allowlist_model() -> None:
    user_client = FakeUserClient(
        result=CurrentUser(
            user_id=1,
            username="admin",
            real_name="管理员",
            roles=["admin"],
            permissions=["system:read"],
        )
    )

    response = asyncio.run(
        _request(
            user_client=user_client,
            cookies={"genstack_session": " private-token "},
        )
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": 1,
        "username": "admin",
        "real_name": "管理员",
        "dept_id": None,
        "dept_name": None,
        "company_id": None,
        "roles": ["admin"],
        "permissions": ["system:read"],
        "menu_permissions": [],
        "role_permissions": [],
    }
    assert user_client.calls == ["private-token"]
    assert "token" not in response.text.lower()


def test_current_user_requires_userinfo_configuration() -> None:
    user_client = FakeUserClient()

    response = asyncio.run(
        _request(
            user_client=user_client,
            settings=Settings(_env_file=None),
            cookies={"genstack_session": "private-token"},
        )
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "第三方用户信息配置不完整"}
    assert user_client.calls == []


def test_current_user_clears_cookie_when_remote_session_is_rejected() -> None:
    user_client = FakeUserClient(error=RemoteAuthenticationError("private-token"))
    settings = Settings(
        _env_file=None,
        oauth2_userinfo_url="https://auth.example/oauth2/userinfo",
        auth_cookie_secure=True,
    )

    response = asyncio.run(
        _request(
            user_client=user_client,
            settings=settings,
            cookies={"genstack_session": "private-token"},
        )
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "登录已失效"}
    cookie = response.headers["set-cookie"]
    assert cookie.startswith('genstack_session=""')
    assert "Max-Age=0" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Secure" in cookie
    assert "private-token" not in response.text


def test_current_user_maps_remote_failure_to_stable_gateway_error() -> None:
    user_client = FakeUserClient(
        error=RemoteServiceError("sensitive upstream private-token")
    )

    response = asyncio.run(
        _request(
            user_client=user_client,
            cookies={"genstack_session": "private-token"},
        )
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "第三方用户信息暂时不可用"}
    assert "private-token" not in response.text
