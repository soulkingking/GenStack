import asyncio
import logging
from collections.abc import Callable

import httpx
import pytest

from app.clients.base import RemoteAuthenticationError, RemoteServiceError
from app.clients.user import CurrentUser, UserClient

_USERINFO_URL = "https://auth.example/oauth2/userinfo"


async def _get_current_user(
    handler: Callable[[httpx.Request], httpx.Response],
) -> CurrentUser:
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        return await UserClient(_USERINFO_URL, client).get_current_user("private-token")


def test_user_client_sends_bearer_token_and_maps_only_allowed_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url == httpx.URL(_USERINFO_URL)
        assert request.headers["authorization"] == "Bearer private-token"
        return httpx.Response(
            200,
            json={
                "code": 200,
                "success": True,
                "result": {
                    "userId": 1,
                    "username": "admin",
                    "realName": "管理员",
                    "deptId": 10,
                    "deptName": "平台部门",
                    "companyId": 20,
                    "roles": ["admin"],
                    "permissions": ["system:read"],
                    "menuPermission": ["dashboard"],
                    "rolePermission": ["ROLE_ADMIN"],
                    "token": "remote-session-token",
                    "thirdToken": "remote-third-token",
                    "refreshToken": "remote-refresh-token",
                    "unknown": "ignored",
                },
            },
        )

    user = asyncio.run(_get_current_user(handler))

    assert user == CurrentUser(
        user_id=1,
        username="admin",
        real_name="管理员",
        dept_id=10,
        dept_name="平台部门",
        company_id=20,
        roles=["admin"],
        permissions=["system:read"],
        menu_permissions=["dashboard"],
        role_permissions=["ROLE_ADMIN"],
    )
    serialized = user.model_dump()
    assert "token" not in serialized
    assert "unknown" not in serialized


def test_user_client_normalizes_missing_and_invalid_optional_fields() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 200,
                "success": True,
                "result": {
                    "userId": "not-an-integer",
                    "username": 123,
                    "roles": ["admin", 1, None],
                    "permissions": None,
                },
            },
        )

    user = asyncio.run(_get_current_user(handler))

    assert user.user_id is None
    assert user.username is None
    assert user.roles == ["admin"]
    assert user.permissions == []
    assert user.menu_permissions == []
    assert user.role_permissions == []


@pytest.mark.parametrize("status_code", [401, 403])
def test_user_client_classifies_remote_authentication_failure(
    status_code: int,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code)

    with pytest.raises(RemoteAuthenticationError):
        asyncio.run(_get_current_user(handler))


def test_user_client_classifies_remote_http_failure() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="sensitive upstream body")

    with pytest.raises(RemoteServiceError):
        asyncio.run(_get_current_user(handler))


def test_user_client_logs_request_metadata_and_masks_debug_body(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 200,
                "success": True,
                "result": {"username": "admin", "token": "remote-session-token"},
            },
        )

    with caplog.at_level(logging.DEBUG, logger="app.clients.base"):
        asyncio.run(_get_current_user(handler))

    assert f"GET {_USERINFO_URL} -> 200" in caplog.text
    assert '"username": "admin"' in caplog.text
    # 请求头 Bearer Token 与远程返回的 token 字段都不允许出现在日志里。
    assert "private-token" not in caplog.text
    assert "remote-session-token" not in caplog.text


def test_user_client_classifies_transport_failure_without_logging_token(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed for private-token", request=request)

    with pytest.raises(RemoteServiceError):
        asyncio.run(_get_current_user(handler))

    assert "private-token" not in caplog.text


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="<html>not json</html>"),
        httpx.Response(
            200,
            json={"code": 1000, "success": False, "result": {"userId": 1}},
        ),
        httpx.Response(200, json={"code": 200, "success": True, "result": []}),
    ],
)
def test_user_client_rejects_invalid_business_response(
    response: httpx.Response,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return response

    with pytest.raises(RemoteServiceError):
        asyncio.run(_get_current_user(handler))
