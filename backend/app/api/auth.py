import logging
import secrets
import time
from collections.abc import AsyncIterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, field_validator

from app.core.config import Settings, get_settings
from app.core.logging import masked_response_preview

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

STATE_COOKIE_NAME = "oauth_state"
SESSION_COOKIE_NAME = "genstack_session"
_TOKEN_REQUEST_TIMEOUT_SECONDS = 10.0


class TokenExchangeRequest(BaseModel):
    """浏览器回调后提交的一次性 OAuth2 授权信息。"""

    code: str
    state: str

    @field_validator("code", "state")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        """清理回调参数并拒绝仅包含空白字符的值。"""

        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned


class SessionStatus(BaseModel):
    """不暴露 Token 的浏览器会话状态。"""

    enabled: bool
    authenticated: bool


def get_auth_settings() -> Settings:
    """返回认证路由使用的运行时配置，并保留测试替换边界。"""

    return get_settings()


def ensure_authentication_enabled(settings: Settings) -> None:
    """在第三方登录开关关闭时拒绝访问登录相关接口。"""

    if not settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="第三方登录未启用",
        )


def require_enabled_authentication(
    settings: Settings = Depends(get_auth_settings),
) -> Settings:
    """返回运行时配置，并保证第三方登录开关已开启。"""

    ensure_authentication_enabled(settings)
    return settings


def require_session_token(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> str:
    """返回清理后的服务端会话 Token，缺失时拒绝继续访问。"""

    if not session_token or not session_token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
        )
    return session_token.strip()


def clear_session_cookie(response: Response, settings: Settings) -> None:
    """使用与创建时相同的属性删除浏览器会话 Cookie。"""

    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )


async def get_oauth_client() -> AsyncIterator[httpx.AsyncClient]:
    """创建仅供一次请求使用的第三方认证服务 HTTP 客户端。"""

    async with httpx.AsyncClient(timeout=_TOKEN_REQUEST_TIMEOUT_SECONDS) as client:
        yield client


def _require_oauth_configuration(settings: Settings) -> None:
    if not settings.oauth2_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="第三方登录配置不完整",
        )


def _build_authorize_url(settings: Settings, state_value: str) -> str:
    parts = urlsplit(settings.oauth2_authorize_url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.extend(
        (
            ("response_type", "code"),
            ("client_id", settings.oauth2_client_id),
            ("redirect_uri", settings.oauth2_redirect_uri),
            ("scope", settings.oauth2_scope),
            ("state", state_value),
        )
    )
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


def _session_ttl(expires_in: object, settings: Settings) -> int:
    # expires_in 来自远程响应；拒绝 bool、字符串和非正数，避免异常 Cookie。
    if (
        isinstance(expires_in, int)
        and not isinstance(expires_in, bool)
        and expires_in > 0
    ):
        return expires_in
    return settings.oauth2_default_session_ttl_seconds


@router.get("/session", response_model=SessionStatus)
def session_status(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    settings: Settings = Depends(get_auth_settings),
) -> SessionStatus:
    """返回第三方登录开关状态，以及浏览器是否持有未过期的登录 Cookie。"""

    # 开关关闭时会话一律视为匿名，避免残留 Cookie 让前端误入登录流程。
    return SessionStatus(
        enabled=settings.auth_enabled,
        authenticated=bool(
            settings.auth_enabled and session_token and session_token.strip()
        ),
    )


@router.get("/login")
def login(
    settings: Settings = Depends(require_enabled_authentication),
) -> RedirectResponse:
    """建立短期 state Cookie，并跳转到第三方 OAuth2 授权页面。"""

    _require_oauth_configuration(settings)
    state_value = secrets.token_urlsafe(32)
    response = RedirectResponse(
        _build_authorize_url(settings, state_value),
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(
        STATE_COOKIE_NAME,
        state_value,
        max_age=settings.oauth2_state_ttl_seconds,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    return response


@router.post("/token", response_model=SessionStatus)
async def exchange_token(
    payload: TokenExchangeRequest,
    response: Response,
    state_cookie: str | None = Cookie(default=None, alias=STATE_COOKIE_NAME),
    settings: Settings = Depends(require_enabled_authentication),
    client: httpx.AsyncClient = Depends(get_oauth_client),
) -> SessionStatus:
    """校验回调状态、在服务端兑换 Token，并建立 HttpOnly Cookie 会话。"""

    _require_oauth_configuration(settings)
    if not state_cookie or not secrets.compare_digest(payload.state, state_cookie):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="登录状态校验失败",
        )

    # client_secret 是远程服务的隐式必填参数，只能从服务端配置注入。
    form = {
        "grant_type": "authorization_code",
        "code": payload.code,
        "client_id": settings.oauth2_client_id,
        "client_secret": settings.oauth2_client_secret.get_secret_value(),
        # 远程服务会与签发 code 时的 redirect_uri 做严格一致性校验。
        "redirect_uri": settings.oauth2_redirect_uri,
    }
    # 只记录地址与状态；表单含 client_secret，任何级别都不得进入日志。
    logger.info("第三方认证服务 Token 请求: POST %s", settings.oauth2_token_url)
    started = time.perf_counter()
    try:
        upstream = await client.post(
            settings.oauth2_token_url,
            data=form,
            timeout=_TOKEN_REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        logger.warning("第三方认证服务 Token 请求失败: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="第三方认证服务暂时不可用",
        ) from exc

    logger.info(
        "第三方认证服务 Token 响应: POST %s -> %s (%.0f ms)",
        settings.oauth2_token_url,
        upstream.status_code,
        (time.perf_counter() - started) * 1000,
    )
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("第三方认证服务 Token 响应正文: %s", masked_response_preview(upstream))

    if not upstream.is_success:
        logger.warning(
            "第三方认证服务 Token 请求返回非成功 HTTP 状态: %s",
            upstream.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="第三方认证服务暂时不可用",
        )

    try:
        body = upstream.json()
    except ValueError as exc:
        logger.warning("第三方认证服务 Token 响应不是合法 JSON")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="第三方登录失败",
        ) from exc

    result = body.get("result") if isinstance(body, dict) else None
    access_token = result.get("access_token") if isinstance(result, dict) else None
    if (
        not isinstance(body, dict)
        or body.get("code") != 200
        or body.get("success") is not True
        or not isinstance(access_token, str)
        or not access_token.strip()
    ):
        logger.warning("第三方认证服务 Token 响应未通过业务契约校验")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="第三方登录失败",
        )

    response.set_cookie(
        SESSION_COOKIE_NAME,
        access_token.strip(),
        max_age=_session_ttl(result.get("expires_in"), settings),
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    response.delete_cookie(
        STATE_COOKIE_NAME,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return SessionStatus(enabled=True, authenticated=True)
