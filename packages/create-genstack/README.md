# create-genstack

从 [GenStack](https://github.com/soulkingking/GenStack) 模板（React 19 + FastAPI
单仓库）创建新项目。

```bash
npm create genstack@latest -- my-app
# 或
npx create-genstack my-app [target-dir] [--repo <url>] [--ref <branch>]
```

CLI 克隆模板仓库后委托模板内的 `scripts/create-project.sh` 完成文件复制、
项目标识替换（`my-app` → 显示名 `MyApp`）、版本重置和 git 初始化。
需要 `git` 与 `bash`（Windows 请在 Git Bash 中执行）。

发布：

```bash
cd packages/create-genstack && npm publish
```
