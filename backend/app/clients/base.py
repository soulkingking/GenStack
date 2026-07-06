import logging
import time
from typing import Any

import httpx

from app.core.logging import masked_response_preview

logger = logging.getLogger(__name__)

# 分开限制连接和整体网络等待，避免远程服务异常时长期占用应用请求。
REMOTE_REQUEST_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class RemoteClientError(Exception):
    """远程客户端可在本站 API 边界安全转换的基础异常。"""


class RemoteAuthenticationError(RemoteClientError):
    """远程服务拒绝了当前 Access Token。"""


class RemoteServiceError(RemoteClientError):
    """远程服务未能提供符合约定的业务响应。"""


class RemoteClient:
    """封装携带 Bearer Token 的远程请求和公共响应校验。"""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http_client = http_client

    async def get_result(self, url: str, access_token: str) -> dict[str, Any]:
        """请求远程接口并返回通过业务契约校验的 result 对象。

        Raises:
            RemoteAuthenticationError: 远程服务返回 401 或 403。
            RemoteServiceError: 网络、HTTP 状态或业务响应不符合约定。
        """

        logger.info("远程服务请求: GET %s", url)
        started = time.perf_counter()
        try:
            response = await self._http_client.get(
                url,
                # Token 只能进入请求头；日志和异常消息不得包含该请求头。
                headers={"Authorization": f"Bearer {access_token.strip()}"},
                timeout=REMOTE_REQUEST_TIMEOUT,
            )
        except httpx.HTTPError as exc:
            logger.warning("远程服务请求失败: GET %s (%s)", url, type(exc).__name__)
            raise RemoteServiceError("远程服务暂时不可用") from exc

        logger.info(
            "远程服务响应: GET %s -> %s (%.0f ms)",
            url,
            response.status_code,
            (time.perf_counter() - started) * 1000,
        )
        # 正文预览只在 DEBUG 级别输出，敏感字段已掩码；常规日志不含第三方正文。
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("远程服务响应正文: %s", masked_response_preview(response))

        if response.status_code in {
            httpx.codes.UNAUTHORIZED,
            httpx.codes.FORBIDDEN,
        }:
            logger.warning("远程服务拒绝当前会话: %s", response.status_code)
            raise RemoteAuthenticationError("远程会话已失效")

        if not response.is_success:
            logger.warning("远程服务返回非成功 HTTP 状态: %s", response.status_code)
            raise RemoteServiceError("远程服务暂时不可用")

        try:
            body = response.json()
        except ValueError as exc:
            logger.warning("远程服务响应不是合法 JSON")
            raise RemoteServiceError("远程服务响应无效") from exc

        result = body.get("result") if isinstance(body, dict) else None
        if (
            not isinstance(body, dict)
            or body.get("code") != 200
            or body.get("success") is not True
            or not isinstance(result, dict)
        ):
            # 警告不含正文，防止第三方错误信息进入常规日志；排查时开 DEBUG 看掩码预览。
            logger.warning("远程服务响应未通过业务契约校验")
            raise RemoteServiceError("远程服务响应无效")

        return result
