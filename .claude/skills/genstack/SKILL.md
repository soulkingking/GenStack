---
name: genstack
description: 用 GenStack 模板（React 19 + FastAPI 全栈单仓库）创建新项目。Trigger 用户说「创建/新建 genstack 项目」「用 GenStack 模板搭建 xxx」「create a genstack project」，或 /genstack <project-name> [target-dir]。
---

# GenStack 项目脚手架

从 GenStack 模板创建全栈新项目（React 19 + Vite + Tailwind + shadcn/ui 前端，
FastAPI 后端，可选 Nacos 注册，Docker 单镜像交付）。

## 命名规则

- slug：小写字母开头，仅含小写字母、数字、连字符（如 `my-app`），用作镜像名、
  Compose 项目名、pnpm scope、Nacos 服务名
- 显示名自动派生 PascalCase（`my-app` → `MyApp`）
- 用户未给出名称时，根据其项目描述提议一个 slug 并确认

## 创建方式（按序尝试）

1. 当前目录在模板仓库内（仓库根有 `scripts/create-project.sh`）：

   ```bash
   bash scripts/create-project.sh <name> [target-dir]
   ```

2. 否则远程自举：

   ```bash
   curl -fsSL https://raw.githubusercontent.com/soulkingking/GenStack/main/scripts/create-project.sh \
     | bash -s -- <name> [target-dir]
   ```

   或（npm 已发布时）`npm create genstack@latest -- <name>`。

target-dir 默认为当前目录下 `<name>/`，且不能位于模板仓库内部。脚本会替换全部
项目标识、重置 VERSION/CHANGELOG、生成 .env、初始化 git 仓库，并自动安装前后端
依赖（`--skip-install` 跳过），无交互。

## 创建后必做

1. 按用户的项目描述改写新项目 `README.md` 的简介段落
2. 核对 `.env`：`NACOS_ENABLED`（不用服务发现就设 false）、`NACOS_SERVER_ADDR`、
   `AUTH_USERNAME`/`AUTH_PASSWORD`
3. 运行验证（依赖已自动安装；若被跳过或失败，先按新项目 README「本地开发」补装）：

   ```bash
   (cd backend && .venv/bin/pytest -q)
   corepack pnpm --dir frontend check
   ```

4. 用户描述了业务功能时，验证通过后再实现首个接口/页面；后端路由加在
   `backend/app/api/`，前端页面加在 `frontend/src/pages/`
