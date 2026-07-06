from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.clients.base import RemoteClient


class CurrentUser(BaseModel):
    """本站允许返回给浏览器的当前用户字段。"""

    user_id: int | None = None
    username: str | None = None
    real_name: str | None = None
    dept_id: int | None = None
    dept_name: str | None = None
    company_id: int | None = None
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    menu_permissions: list[str] = Field(default_factory=list)
    role_permissions: list[str] = Field(default_factory=list)


def _optional_integer(value: object) -> int | None:
    # bool 是 int 的子类，但不能作为业务主键返回。
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


class UserClient:
    """通过远程用户信息接口读取并映射当前用户。"""

    def __init__(self, userinfo_url: str, http_client: httpx.AsyncClient) -> None:
        self._userinfo_url = userinfo_url
        self._remote = RemoteClient(http_client)

    async def get_current_user(self, access_token: str) -> CurrentUser:
        """获取当前用户，并丢弃远程响应中不在白名单内的字段。"""

        result: dict[str, Any] = await self._remote.get_result(
            self._userinfo_url,
            access_token,
        )
        # 显式逐字段映射是安全边界，禁止把远程对象整体透传给浏览器。
        return CurrentUser(
            user_id=_optional_integer(result.get("userId")),
            username=_optional_string(result.get("username")),
            real_name=_optional_string(result.get("realName")),
            dept_id=_optional_integer(result.get("deptId")),
            dept_name=_optional_string(result.get("deptName")),
            company_id=_optional_integer(result.get("companyId")),
            roles=_string_list(result.get("roles")),
            permissions=_string_list(result.get("permissions")),
            menu_permissions=_string_list(result.get("menuPermission")),
            role_permissions=_string_list(result.get("rolePermission")),
        )
