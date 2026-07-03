# GenStack backend

后端是最小 FastAPI 应用，提供 `/api/health`、`/api/meta`、生产静态资源托管，
以及可选的 Nacos 服务注册（`NACOS_ENABLED=true` 时启动注册、关闭时注销，
注册失败只记录日志不阻止启动）。配置由 `app/core/config.py` 从环境变量及仓库根
`.env` 读取，其中认证账号为预留配置，登录接口尚未实现。

本地测试：

```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -q
# Windows PowerShell: cd backend; .venv\Scripts\pytest -q
```
