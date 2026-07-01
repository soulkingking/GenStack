# Docker 国内源、时区与 VS Code 运行配置设计

## 目标

在不改变 GenStack 应用架构和固定端口契约的前提下：

- 为多阶段 Docker 构建补齐默认国内基础镜像和包管理镜像；
- 允许通过构建参数切回官方镜像与源；
- 在运行镜像中完整安装并配置 `Asia/Shanghai` 时区；
- 为 macOS 开发环境提供可直接使用的 VS Code 后端、前端、浏览器和全栈调试配置。

## Docker 镜像与包源

`Dockerfile` 保持 Node 前端构建、Python 后端运行的双阶段结构。以下参数均提供国内
默认值，并允许在 `docker build` 时覆盖：

| 参数 | 默认值 | 用途 |
| --- | --- | --- |
| `NODE_IMAGE` | `docker.m.daocloud.io/library/node:22-bookworm-slim` | 前端基础镜像 |
| `PYTHON_IMAGE` | `docker.m.daocloud.io/library/python:3.11-slim-bookworm` | 运行时基础镜像 |
| `NPM_REGISTRY` | `https://registry.npmmirror.com` | pnpm 依赖下载 |
| `PIP_INDEX_URL` | `https://mirrors.aliyun.com/pypi/simple/` | Python 依赖下载 |
| `DEBIAN_MIRROR` | `mirrors.tuna.tsinghua.edu.cn` | Debian 软件包下载 |
| `TZ` | `Asia/Shanghai` | 容器系统时区 |

基础镜像参数在第一个 `FROM` 前声明，使两个构建阶段都能引用。阶段内部使用的参数
分别在对应阶段声明，避免依赖跨阶段的隐式参数作用域。

pnpm 继续作为前端唯一依赖管理器。Node 镜像内通过 npm 的国内 registry 安装项目
固定版本的 pnpm，然后使用 `pnpm install --frozen-lockfile`，不引入 npm lockfile。

## 时区

Python 运行阶段执行以下操作：

- 同时兼容 Debian 的 `/etc/apt/sources.list` 与
  `/etc/apt/sources.list.d/debian.sources`；
- 使用 `DEBIAN_FRONTEND=noninteractive` 安装 `ca-certificates` 和 `tzdata`；
- 将 `/etc/localtime` 链接到 `/usr/share/zoneinfo/${TZ}`；
- 将 `${TZ}` 写入 `/etc/timezone`；
- 保留 `TZ` 环境变量；
- 删除 apt 列表，避免扩大最终镜像层。

时区设置只存在于 Python 运行阶段。前端构建不需要系统时区数据。

## 构建脚本

`scripts/package.sh` 继续先验证前端依赖和构建，再执行 Docker 构建。脚本读取可选同名
环境变量，并明确传递六个 `--build-arg`。未设置时使用与 `Dockerfile` 相同的国内
默认值，确保直接执行脚本和直接执行 `docker build` 行为一致。

README 同时提供国内默认构建命令和切换官方源的完整示例。

## VS Code 配置

新增以下文件：

- `.vscode/extensions.json`
- `.vscode/settings.json`
- `.vscode/tasks.json`
- `.vscode/launch.json`

扩展推荐包含 Python、debugpy、Tailwind CSS、Oxc 和 Docker，不包含 Vue 扩展。

工作区设置固定 Python 解释器为 `backend/.venv/bin/python`，配置
`backend` 分析路径，并启用 `backend/tests` 的 pytest 发现。

任务配置面向当前 macOS 环境，使用 `bash` 和 `lsof` 清理端口：

- `debug: kill backend port 8000`
- `debug: kill frontend port 5173`

端口没有监听进程时任务正常成功，不产生 `kill` 参数错误。

运行配置包含：

- `Python: FastAPI (后端)`：无热重载，适合稳定断点；
- `Python: FastAPI (后端, 热重载)`：开发时自动重启；
- `pnpm: 前端开发 (Vite)`：使用 `corepack pnpm dev`；
- `Chrome: 前端页面`：打开 `http://127.0.0.1:5173` 并启用源码映射；
- `全栈: 后端调试 + Vite`：并行启动后端普通调试和 Vite，停止 compound 时终止两者。

浏览器配置不加入全栈 compound，避免 Chrome 在 Vite 就绪前启动产生竞态。需要浏览器
断点时，在全栈服务就绪后单独启动 Chrome 配置。

## 文档与忽略规则

`.gitignore` 放行 `.vscode/settings.json`。README 增加：

- VS Code 首次准备与运行配置说明；
- 国内默认 Docker 构建说明；
- 切换官方镜像与包源示例。

`docs/调试标准.md` 同步固定端口任务、运行配置名称和推荐调试顺序。

## 验证

- 使用 Node 解析四个 `.vscode/*.json` 文件；
- 使用 `bash -n` 检查 `scripts/package.sh`；
- 运行 macOS 端口清理命令的空端口路径；
- 使用 Ruby 解析 `docker-compose.yml`；
- 运行后端测试和前端 `check`；
- 审查最终 diff 的注释与文档；
- 在 Docker 可用环境中构建镜像，并验证：
  - `/etc/timezone` 等于 `Asia/Shanghai`；
  - `/etc/localtime` 指向对应 zoneinfo；
  - `/api/health` 正常响应。

当前机器没有 Docker CLI，因此本次只能完成 Dockerfile 静态审查；镜像构建和容器内
时区检查必须在具备 Docker 的机器上执行，并在交付结果中明确标注。
