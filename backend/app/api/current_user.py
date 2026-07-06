from collections.abc import AsyncIterator

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.auth import clear_session_cookie, require_session_token
from app.clients.base import RemoteAuthenticationError, RemoteClientError
from app.clients.user import CurrentUser, UserClient
from app.core.config import Settings, get_settings

router = APIRouter(tags=["current-user"])


def get_current_user_settings() -> Settings:
    """返回当前用户接口配置，并保留测试替换边界。"""

    return get_settings()


async def get_remote_http_client() -> AsyncIterator[httpx.AsyncClient]:
    """创建当前请求范围内复用的异步远程 HTTP 客户端。"""

    async with httpx.AsyncClient() as client:
        yield client


def get_user_client(
    settings: Settings = Depends(get_current_user_settings),
    http_client: httpx.AsyncClient = Depends(get_remote_http_client),
) -> UserClient:
    """构造只依赖远程协议的用户客户端。"""

    return UserClient(settings.oauth2_userinfo_url, http_client)


@router.get("/current-user", response_model=CurrentUser)
async def read_current_user(
    access_token: str = Depends(require_session_token),
    settings: Settings = Depends(get_current_user_settings),
    user_client: UserClient = Depends(get_user_client),
) -> CurrentUser | JSONResponse:
    """使用 HttpOnly Cookie 中的 Token 获取经过白名单过滤的当前用户。"""

    if not settings.oauth2_userinfo_url.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="第三方用户信息配置不完整",
        )

    try:
        return await user_client.get_current_user(access_token)
    except RemoteAuthenticationError:
        # 远程服务已拒绝 Token，必须同时清理本站 Cookie，避免前端反复使用失效会话。
        response = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "登录已失效"},
        )
        clear_session_cookie(response, settings)
        return response
    except RemoteClientError as exc:
        # 对外保持稳定错误，不透传可能含远程实现细节的异常消息。
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="第三方用户信息暂时不可用",
        ) from exc
