from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class SpaStaticFiles(StaticFiles):
    """支持前端路由深链接的单页应用静态资源服务。"""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            # 无扩展名的未知路径视为前端路由，回退到 index.html 交给 React Router；
            # 带扩展名的资源缺失仍返回 404，避免掩盖构建产物问题。
            last_segment = path.rsplit("/", 1)[-1]
            if exc.status_code == 404 and "." not in last_segment:
                return await super().get_response("index.html", scope)
            raise
