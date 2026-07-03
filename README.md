# GenStack

GenStack 是一个采用 React 与 FastAPI 的最小全栈项目模板。它沿用
[quick-project-template](https://gitee.com/numen06/quick-project-template) 的单仓库、
固定端口、单镜像和 `data/` 持久化约定，但前端使用 React 技术栈。

## 当前能力

- `GET /api/health`：API 存活检查
- `GET /api/meta`：应用名称和版本
- React 状态首页
- Vite 开发代理
- FastAPI 同源静态资源托管（支持前端路由深链接回退到 index.html）
- 可选 Nacos 服务注册：`NACOS_ENABLED=true` 时启动注册实例、关闭时注销
- Docker Compose 单容器交付

当前不包含登录接口、用户管理、API Key、ORM 或数据库迁移。认证账号
（`AUTH_USERNAME`/`AUTH_PASSWORD`）与 `DATABASE_URL` 一样属于预留配置。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 | Python 3.11、FastAPI、pydantic-settings |
| 前端 | React 19、Vite 8、TypeScript 6、pnpm、Tailwind CSS、shadcn/ui、TanStack Query |
| 数据 | 预留 `DATABASE_URL`，默认持久化目录为 `data/` |
| 服务发现 | 可选 Nacos（nacos-sdk-python，默认关闭） |
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
(cd backend && .venv/bin/pytest -q)
corepack pnpm --dir frontend check
docker compose config --quiet
```

推送到 `main` 或提交 PR 时，GitHub Actions（[.github/workflows/ci.yml](.github/workflows/ci.yml)）
自动执行同样的后端测试、前端检查和 Compose 配置校验。

## Docker

默认使用 DaoCloud 基础镜像、npmmirror、阿里云 PyPI 和清华 Debian 源：

```bash
bash scripts/package.sh
docker compose up -d
```

访问 <http://127.0.0.1:8000>。容器内由 FastAPI 同时提供静态页面和 API，系统时区
默认为 `Asia/Shanghai`。

需要切回官方源时：

```bash
NODE_IMAGE=node:22-bookworm-slim \
PYTHON_IMAGE=python:3.11-slim-bookworm \
NPM_REGISTRY=https://registry.npmjs.org \
PIP_INDEX_URL=https://pypi.org/simple \
DEBIAN_MIRROR=deb.debian.org \
TZ=UTC \
bash scripts/package.sh
```

所有变量都只影响本次构建，不会写入仓库配置。

## VS Code

首次使用前完成本地依赖安装，然后接受工作区推荐扩展。运行和调试面板提供：

- `Python: FastAPI (后端)`：稳定断点调试；
- `Python: FastAPI (后端, 热重载)`：后端热更新；
- `pnpm: 前端开发 (Vite)`：启动 React 开发服务器；
- `Chrome: 前端页面`：连接前端源码调试；
- `全栈: 后端调试 + Vite`：同时启动前后端。

启动配置会先清理固定端口 `8000` 或 `5173`。Chrome 配置应在 Vite 就绪后单独启动，
避免浏览器和开发服务器启动竞态。

## 文档

- [架构标准](docs/架构标准.md)
- [前端框架标准](docs/前端框架标准.md)
- [调试标准](docs/调试标准.md)
- [版本标准](docs/版本标准.md)
