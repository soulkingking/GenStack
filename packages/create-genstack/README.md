# create-genstack

从 [GenStack](https://github.com/soulkingking/GenStack) 模板（React 19 + FastAPI
单仓库）创建新项目。

```bash
npm create genstack@latest -- my-app
# 或
npx create-genstack my-app [target-dir] [--repo <url>] [--ref <branch>]
```

CLI 为纯 Node 实现，macOS/Linux/Windows（PowerShell/CMD）原生可用：克隆模板
仓库（或 `--template <dir>` 使用本地模板）后完成文件复制、项目标识替换
（`my-app` → 显示名 `MyApp`）、版本重置、git 初始化和前后端依赖安装
（`--skip-install` 跳过）。需要 `git`、Node.js ≥ 22 与 Python 3.11（推荐 uv）。

发布：

```bash
cd packages/create-genstack && npm publish
```
