from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """返回 API 进程是否能够接收请求。"""

    return {"status": "ok"}
