# GenStack backend

后端是 FastAPI 应用，提供 `/api/health`、`/api/meta`、OAuth2 登录、生产静态资源
托管，以及可选的 Nacos 服务注册（`NACOS_ENABLED=true` 时启动注册、关闭时注销，
注册失败只记录日志不阻止启动）。配置由 `app/core/config.py` 从环境变量及仓库根
`.env` 读取。

认证接口：

- `GET /api/auth/session`：返回当前浏览器是否已有登录 Cookie。
- `GET /api/auth/login`：生成 `state` 并跳转 JBM 授权页。
- `POST /api/auth/token`：校验 `state`、在后端兑换 Token 并设置 HttpOnly Cookie。

`OAUTH2_CLIENT_SECRET` 只能配置在后端环境。Token 接口使用 JBM 支持的
`POST application/x-www-form-urlencoded`，避免密钥进入 URL。当前不实现 Refresh
Token、登出、用户同步或业务接口代理。

本地测试：

```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -q
# Windows PowerShell: cd backend; .venv\Scripts\pytest -q
```
