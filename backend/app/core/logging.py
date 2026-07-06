import json
import logging

import httpx

# 命中这些关键字的字段在日志中一律掩码，覆盖 Token、密钥和凭据类命名。
_SENSITIVE_KEY_MARKERS = ("token", "secret", "password", "authorization", "cookie")
_BODY_PREVIEW_LIMIT = 2000
_MASK = "***"


def configure_logging(debug: bool) -> None:
    """初始化应用日志输出。

    uvicorn 只配置自身 logger，应用模块的 INFO 日志需要根处理器才会显示。
    """

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    # httpx 的请求日志与应用日志重复；httpcore/grpc 的 DEBUG 输出过密，一并压低。
    for noisy_logger in ("httpx", "httpcore", "grpc", "watchfiles"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def _masked(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _MASK
            if any(marker in str(key).lower() for marker in _SENSITIVE_KEY_MARKERS)
            else _masked(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_masked(item) for item in value]
    return value


def _truncated(text: str) -> str:
    if len(text) <= _BODY_PREVIEW_LIMIT:
        return text
    return f"{text[:_BODY_PREVIEW_LIMIT]}...(截断，共 {len(text)} 字符)"


def masked_response_preview(response: httpx.Response) -> str:
    """返回适合写入日志的响应正文预览：敏感字段掩码、超长截断。"""

    try:
        body = response.json()
    except ValueError:
        return _truncated(response.text)
    return _truncated(json.dumps(_masked(body), ensure_ascii=False))
