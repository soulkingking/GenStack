# GenStack

GenStack 是一个采用 React 与 FastAPI 的最小全栈项目模板。它沿用
[quick-project-template](https://gitee.com/numen06/quick-project-template) 的单仓库、
固定端口、单镜像和 `data/` 持久化约定，但前端使用 React 技术栈。

## 当前能力

- `GET /api/health`：API 存活检查
- `GET /api/meta`：应用名称和版本
- React 状态首页
- 第三方 OAuth2 授权码登录（FastAPI 服务端换取 Token）
- HttpOnly Cookie 登录会话与 OAuth2 `state` 校验
- `GET /api/current-user`：由后端查询并过滤当前用户信息
- Vite 开发代理
- FastAPI 同源静态资源托管（支持前端路由深链接回退到 index.html）
- 可选 Nacos 服务注册：`NACOS_ENABLED=true` 时启动注册实例、关闭时注销
- Docker Compose 单容器交付

当前不包含用户同步、权限模型、Token 刷新、主动登出、API Key、ORM 或数据库迁移。
第三方 Access Token 只保存在后端设置的 HttpOnly Cookie 中，前端 JavaScript
不能读取。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 | Python 3.11、FastAPI、pydantic-settings |
| 前端 | React 19、Vite 8、TypeScript 6、pnpm、Tailwind CSS、shadcn/ui、TanStack Query |
| 数据 | 预留 `DATABASE_URL`，默认持久化目录为 `data/` |
| 服务发现 | 可选 Nacos（nacos-sdk-python，默认关闭） |
| 交付 | 多阶段 Dockerfile、Docker Compose |

<!-- template-only:start -->
## 用模板创建新项目

推荐方式（macOS/Linux/Windows 通用，[packages/create-genstack](packages/create-genstack) 发布到 npm 后可用）：

```bash
npm create genstack@latest -- my-app
```

macOS/Linux 也可用远程一行命令（脚本自举：先克隆模板再执行）：

```bash
curl -fsSL https://raw.githubusercontent.com/soulkingking/GenStack/main/scripts/create-project.sh \
  | bash -s -- my-app
```

本地已有模板仓库时：

```bash
bash scripts/create-project.sh my-app ~/工作/项目/my-app          # macOS/Linux
node packages/create-genstack/bin/create-genstack.mjs --template . my-app  # 全平台
```

所有方式最终都由 `packages/create-genstack`（纯 Node，跨平台）完成：复制模板中受版本管理的文件
（自动跳过 `.git`、依赖与构建产物），把 `GenStack`/`genstack` 全部替换为新项目名
（`my-app` → 显示名 `MyApp`，同时用作 Docker 镜像名、Compose 项目名、pnpm scope
和 Nacos 服务名），重置 VERSION 与 CHANGELOG，从 `.env.example` 生成 `.env`，
初始化全新的 git 仓库，并自动安装前后端依赖（`--skip-install` 可跳过；工具缺失时
回退为打印「本地开发」手动步骤）。依赖安装默认使用阿里云 PyPI 与 npmmirror（与
Dockerfile 一致），可用环境变量 `PIP_INDEX_URL`、`NPM_REGISTRY` 覆盖为官方源；
后端要求 Python >= 3.11（安装 [uv](https://docs.astral.sh/uv/) 可自动下载）。
完成后即可直接启动或在 VS Code 中 F5 调试，
注意检查 README 描述与 `.env` 中的 Nacos、认证配置。模板仓库地址与分支可用环境变量
`GENSTACK_REPO`、`GENSTACK_REF` 或 CLI 的 `--repo`、`--ref` 覆盖。脚手架自身
（本节说明、`scripts/create-project.sh`、`packages/`、genstack skill）不会带入新项目。
<!-- template-only:end -->

## 本地开发

### 环境要求

- Python ≥ 3.11（生产镜像固定 3.11；推荐配合 [uv](https://docs.astral.sh/uv/) 创建虚拟环境）
- Node.js ≥ 22（自带 corepack，用于按 `packageManager` 版本运行 pnpm，无需全局安装 pnpm）
- Docker（可选，仅打包镜像时需要）
- Windows 原生支持（PowerShell/CMD）：开发脚本均为 Node 实现；另需
  [Git for Windows](https://git-scm.com/download/win)。唯一差异是虚拟环境
  路径为 `backend\.venv\Scripts\`（unix 为 `backend/.venv/bin/`）

### 安装依赖

```bash
# 运行时配置
cp .env.example .env    # Windows PowerShell: Copy-Item .env.example .env

# 后端依赖：创建虚拟环境并安装 Python 包
uv venv --python 3.11 --seed backend/.venv
backend/.venv/bin/pip install -r backend/requirements-dev.txt
# Windows: backend\.venv\Scripts\pip install -r backend/requirements-dev.txt

# 前端依赖：按 pnpm-lock.yaml 锁定版本安装 node 包
node scripts/init-frontend.mjs
# 等价于: corepack pnpm --dir frontend install --frozen-lockfile
```

未安装 `uv` 时，可用系统 Python（>= 3.11）创建虚拟环境：

```bash
python3 -m venv backend/.venv    # Windows: py -m venv backend\.venv（需 >= 3.11）
```

### 启动

分别启动两个进程（全平台一致）：

```bash
node scripts/start-backend.mjs
node scripts/start-frontend.mjs
```

访问 <http://127.0.0.1:5173>。后端固定使用
<http://127.0.0.1:8000>，Vite 将 `/api` 代理到该端口。

### 配置第三方登录

在第三方认证服务注册 OAuth2 客户端，并把回调地址设置为与 `.env` 中
`OAUTH2_REDIRECT_URI` 完全相同的值。本地默认回调地址为
`http://127.0.0.1:5173/`。然后配置：

```dotenv
OAUTH2_AUTHORIZE_URL=http://127.0.0.1:5555/oauth2/authorize
OAUTH2_TOKEN_URL=http://127.0.0.1:5555/oauth2/token
OAUTH2_USERINFO_URL=http://127.0.0.1:5555/oauth2/userinfo
OAUTH2_CLIENT_ID=your-client-id
OAUTH2_CLIENT_SECRET=your-client-secret
OAUTH2_REDIRECT_URI=http://127.0.0.1:5173/
OAUTH2_SCOPE=all
AUTH_COOKIE_SECURE=false
```

浏览器访问系统后先检查本站会话；未登录时由 `/api/auth/login` 跳转第三方认证服务。认证服务
回调携带 `code/state` 后，前端调用 `/api/auth/token`，FastAPI 使用服务端密钥
兑换 Token 并写入 HttpOnly Cookie。生产环境必须使用 HTTPS，并设置
`AUTH_COOKIE_SECURE=true`。

登录后请求 `GET /api/current-user` 时，FastAPI 从 HttpOnly Cookie 读取 Access Token，
通过 `backend/app/clients/` 请求第三方用户信息接口，只向浏览器返回用户、部门、角色和
权限白名单字段。第三方拒绝 Token 时接口清除本站 Cookie 并返回 401；网络或响应契约失败
统一返回 502。

## 验证

```bash
(cd backend && .venv/bin/pytest -q)    # Windows: cd backend; .venv\Scripts\pytest -q
corepack pnpm --dir frontend check
docker compose config --quiet
```

推送到 `main` 或提交 PR 时，GitHub Actions（[.github/workflows/ci.yml](.github/workflows/ci.yml)）
在 Linux 与 Windows 上自动执行同样的后端测试和前端检查（Compose 校验仅 Linux）。

## Docker

默认使用 DaoCloud 基础镜像、npmmirror、阿里云 PyPI 和清华 Debian 源：

```bash
node scripts/package.mjs
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
node scripts/package.mjs
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
