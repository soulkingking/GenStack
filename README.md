# GenStack

GenStack 是一个采用 React 与 FastAPI 的最小全栈项目模板。它沿用
[quick-project-template](https://gitee.com/numen06/quick-project-template) 的单仓库、
固定端口、单镜像和 `data/` 持久化约定，但前端使用 React 技术栈。

## 当前能力

- `GET /api/health`：API 存活检查
- `GET /api/meta`：应用名称和版本
- React 状态首页
- Vite 开发代理
- FastAPI 同源静态资源托管
- Docker Compose 单容器交付

当前不包含认证、用户管理、API Key、ORM、数据库迁移或 Nacos。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 | Python 3.11、FastAPI、pydantic-settings |
| 前端 | React 19、Vite 8、TypeScript 6、pnpm、Tailwind CSS、shadcn/ui、TanStack Query |
| 数据 | 预留 `DATABASE_URL`，默认持久化目录为 `data/` |
| 交付 | 多阶段 Dockerfile、Docker Compose |

## 本地开发

```bash
cp .env.example .env
uv venv --python 3.11 --seed backend/.venv
backend/.venv/bin/pip install -r backend/requirements-dev.txt
bash scripts/init-frontend.sh
```

未安装 `uv` 时，可用系统 Python 3.11 创建虚拟环境：

```bash
python3.11 -m venv backend/.venv
```

分别启动两个进程：

```bash
bash scripts/start-backend.sh
bash scripts/start-frontend.sh
```

访问 <http://127.0.0.1:5173>。后端固定使用
<http://127.0.0.1:8000>，Vite 将 `/api` 代理到该端口。

## 验证

```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -q
corepack pnpm --dir frontend check
docker compose config --quiet
```

## Docker

```bash
bash scripts/package.sh
docker compose up -d
```

访问 <http://127.0.0.1:8000>。容器内由 FastAPI 同时提供静态页面和 API。

## 文档

- [架构标准](docs/架构标准.md)
- [前端框架标准](docs/前端框架标准.md)
- [调试标准](docs/调试标准.md)
- [版本标准](docs/版本标准.md)
