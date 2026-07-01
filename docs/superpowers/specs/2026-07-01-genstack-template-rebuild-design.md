# GenStack 模板重建设计

## 目标

将 GenStack 当前未提交的工作区内容直接删除，以
`https://gitee.com/numen06/quick-project-template.git` 当前模板为基础重新搭建项目。
项目继续使用 `GenStack` 名称、现有 Git 仓库和 GitHub 远端；前端改用 GenStack
现有 React 技术栈，其余结构与运行方式遵循目标模板。

## 替换策略

- 保留当前仓库的 `.git/` 目录、`main` 分支和 `origin`。
- 不创建归档、stash 或备份；直接删除当前所有已跟踪外的项目内容。
- 从目标模板引入后端、容器、脚本、配置、版本和文档结构。
- 不引入目标模板自身的 `.git/` 历史。
- 将模板中的项目名称、镜像名称和说明统一改为 `GenStack`。

该策略会永久移除当前未提交实现。用户已明确选择无备份替换。

## 项目结构

重建后的核心目录如下：

```text
backend/          FastAPI 应用
frontend/         React 单页应用
data/             SQLite 和运行时持久化目录
docs/             项目规范与设计文档
release-notes/    版本发行说明
scripts/          本地启动与镜像打包脚本
Dockerfile        前端构建和后端运行的多阶段镜像
docker-compose.yml
VERSION
README.md
```

## 后端

后端采用目标模板的最小 FastAPI 结构：

- Python 3.11；
- FastAPI、Uvicorn、pydantic-settings；
- 从仓库根目录 `.env` 读取配置；
- `GET /api/health` 提供存活检查；
- `GET /api/meta` 返回 `GenStack` 名称和 `VERSION`；
- 生产镜像中由 FastAPI 托管前端构建产物；
- `data/` 作为默认持久化目录，并保留 `DATABASE_URL` 配置入口。

本次不实现认证、用户管理、API Key、ORM、数据库迁移、Nacos、服务发现或业务接口。
文档不得把这些未实现能力描述为当前功能。

## 前端

前端从零搭建，不复制模板的 Vue 源码。采用：

- React 19；
- Vite 8；
- TypeScript 6；
- pnpm；
- Tailwind CSS；
- shadcn/ui 设计体系；
- TanStack Query；
- React Router；
- Vitest 与 Testing Library。

首版只提供一个最小 GenStack 首页，读取 `/api/health` 和 `/api/meta`，展示应用名称、
版本和服务状态。请求失败时显示明确的不可用状态，不添加认证或管理功能。

开发环境由 Vite 将 `/api` 代理到固定后端端口 `8000`。生产环境前端与 API 使用同一
来源和端口。

## 构建与运行

- 本地后端固定运行在 `127.0.0.1:8000`。
- 本地前端固定运行在 `127.0.0.1:5173`。
- 前端依赖和构建统一使用 pnpm，不保留模板的 npm lockfile。
- Dockerfile 使用 Node 阶段构建前端，再将产物复制到 Python 运行阶段。
- Compose 仅启动一个 `GenStack` 应用容器，并把 `./data` 挂载到 `/app/data`。
- `VERSION` 是应用版本唯一真源；前后端元数据与其保持一致。

## 配置与错误处理

- 提供 `.env.example`，但不提交真实 `.env`。
- CORS 来源通过环境变量配置，默认仅允许本地前端开发地址。
- 前端对网络错误、非成功 HTTP 状态和无效响应提供统一错误状态。
- 后端不把未实现的认证配置或默认账号暴露为可用功能。

## 验证

重建完成后执行以下验证：

- 安装前端依赖并验证 pnpm lockfile；
- 前端 lint、类型检查、单元测试和生产构建；
- 后端导入/启动检查；
- 调用 `/api/health` 和 `/api/meta` 验证响应；
- 构建 Docker 镜像，确认前端静态资源与 API 可由同一容器访问；
- 审查最终 diff，确保注释与文档对应实际实现，不残留 Vue、npm、
  `ai-webapp-template` 或未实现功能的错误说明。
