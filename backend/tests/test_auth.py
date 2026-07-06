import asyncio
from collections.abc import Callable
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi import FastAPI

from app.api import auth
from app.core.config import Settings

_SETTINGS = Settings(
    _env_file=None,
    oauth2_authorize_url="https://auth.example/oauth2/authorize",
    oauth2_token_url="https://auth.example/oauth2/token",
    oauth2_client_id="genstack-client",
    oauth2_client_secret="server-secret",
    oauth2_redirect_uri="http://127.0.0.1:5173/",
    oauth2_scope="all",
)


async def _request(
    method: str,
    path: str,
    *,
    settings: Settings = _SETTINGS,
    upstream_handler: Callable[[httpx.Request], httpx.Response] | None = None,
    **kwargs,
) -> httpx.Response:
    app = FastAPI()
    app.include_router(auth.router, prefix="/api")

    def default_handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("测试未预期调用第三方认证服务")

    upstream = httpx.AsyncClient(
        transport=httpx.MockTransport(upstream_handler or default_handler)
    )
    app.dependency_overrides[auth.get_auth_settings] = lambda: settings
    app.dependency_overrides[auth.get_oauth_client] = lambda: upstream

    try:
        transport = httpx.ASGITransport(app=app)
        cookies = kwargs.pop("cookies", None)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies=cookies,
        ) as client:
            return await client.request(method, path, **kwargs)
    finally:
        await upstream.aclose()


def test_login_redirects_with_state_and_fixed_oauth_parameters() -> None:
    response = asyncio.run(_request("GET", "/api/auth/login"))

    assert response.status_code == 302
    query = parse_qs(urlsplit(response.headers["location"]).query)
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["genstack-client"]
    assert query["redirect_uri"] == ["http://127.0.0.1:5173/"]
    assert query["scope"] == ["all"]
    assert query["state"] == [response.cookies["oauth_state"]]

    state_cookie = response.headers["set-cookie"]
    assert "HttpOnly" in state_cookie
    assert "SameSite=lax" in state_cookie
    assert "Max-Age=300" in state_cookie


def test_login_rejects_incomplete_server_configuration() -> None:
    response = asyncio.run(
        _request("GET", "/api/auth/login", settings=Settings(_env_file=None))
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "第三方登录配置不完整"}


def test_session_only_reports_cookie_presence() -> None:
    authenticated = asyncio.run(
        _request(
            "GET",
            "/api/auth/session",
            cookies={"genstack_session": "private-token"},
        )
    )
    anonymous = asyncio.run(_request("GET", "/api/auth/session"))

    assert authenticated.json() == {"authenticated": True}
    assert "private-token" not in authenticated.text
    assert anonymous.json() == {"authenticated": False}


def test_token_exchange_rejects_mismatched_state_before_calling_provider() -> None:
    response = asyncio.run(
        _request(
            "POST",
            "/api/auth/token",
            json={"code": "one-time-code", "state": "callback-state"},
            cookies={"oauth_state": "expected-state"},
        )
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "登录状态校验失败"}


def test_token_exchange_uses_server_secret_and_sets_http_only_cookie() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == httpx.URL("https://auth.example/oauth2/token")
        assert request.headers["content-type"].startswith(
            "application/x-www-form-urlencoded"
        )
        assert parse_qs(request.content.decode()) == {
            "grant_type": ["authorization_code"],
            "code": ["one-time-code"],
            "client_id": ["genstack-client"],
            "client_secret": ["server-secret"],
            "redirect_uri": ["http://127.0.0.1:5173/"],
        }
        return httpx.Response(
            200,
            json={
                "code": 200,
                "success": True,
                "result": {
                    "access_token": "provider-access-token",
                    "refresh_token": "ignored-refresh-token",
                    "expires_in": 7200,
                },
            },
        )

    response = asyncio.run(
        _request(
            "POST",
            "/api/auth/token",
            json={"code": "one-time-code", "state": "expected-state"},
            cookies={"oauth_state": "expected-state"},
            upstream_handler=handler,
        )
    )

    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
    assert "provider-access-token" not in response.text
    assert response.cookies["genstack_session"] == "provider-access-token"

    cookies = response.headers.get_list("set-cookie")
    session_cookie = next(value for value in cookies if value.startswith("genstack_session="))
    state_cookie = next(value for value in cookies if value.startswith("oauth_state="))
    assert "HttpOnly" in session_cookie
    assert "SameSite=lax" in session_cookie
    assert "Max-Age=7200" in session_cookie
    assert "Max-Age=0" in state_cookie


def test_token_exchange_uses_default_lifetime_for_invalid_expires_in() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 200,
                "success": True,
                "result": {
                    "access_token": "provider-access-token",
                    "expires_in": "invalid",
                },
            },
        )

    response = asyncio.run(
        _request(
            "POST",
            "/api/auth/token",
            json={"code": "one-time-code", "state": "expected-state"},
            cookies={"oauth_state": "expected-state"},
            upstream_handler=handler,
        )
    )

    session_cookie = next(
        value
        for value in response.headers.get_list("set-cookie")
        if value.startswith("genstack_session=")
    )
    assert "Max-Age=3600" in session_cookie


def test_token_exchange_rejects_provider_business_failure_without_leaking_body() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 1000,
                "success": False,
                "message": "invalid secret server-secret",
            },
        )

    response = asyncio.run(
        _request(
            "POST",
            "/api/auth/token",
            json={"code": "one-time-code", "state": "expected-state"},
            cookies={"oauth_state": "expected-state"},
            upstream_handler=handler,
        )
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "第三方登录失败"}
    assert "server-secret" not in response.text
    assert "genstack_session" not in response.cookies


def test_token_exchange_rejects_http_failure_and_missing_access_token() -> None:
    def http_failure(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="upstream token server-secret")

    failed = asyncio.run(
        _request(
            "POST",
            "/api/auth/token",
            json={"code": "one-time-code", "state": "expected-state"},
            cookies={"oauth_state": "expected-state"},
            upstream_handler=http_failure,
        )
    )

    def missing_token(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": 200, "success": True, "result": {}},
        )

    missing = asyncio.run(
        _request(
            "POST",
            "/api/auth/token",
            json={"code": "one-time-code", "state": "expected-state"},
            cookies={"oauth_state": "expected-state"},
            upstream_handler=missing_token,
        )
    )

    assert failed.status_code == 502
    assert failed.json() == {"detail": "第三方认证服务暂时不可用"}
    assert "server-secret" not in failed.text
    assert missing.status_code == 502
    assert missing.json() == {"detail": "第三方登录失败"}
