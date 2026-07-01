# GenStack backend

后端是最小 FastAPI 应用，只提供 `/api/health`、`/api/meta` 和生产静态资源托管。
配置由 `app/core/config.py` 从环境变量及仓库根 `.env` 读取。

本地测试：

```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -q
```
