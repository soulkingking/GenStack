# Docker Mirrors and VS Code Runtime Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add switchable domestic Docker build sources, a complete Asia/Shanghai runtime timezone, and macOS-ready VS Code launch configurations to GenStack.

**Architecture:** Docker build inputs remain reproducible through explicit build arguments whose defaults use domestic mirrors; the package script forwards matching environment variables. VS Code owns editor launch orchestration only, while existing project scripts and fixed ports remain the runtime contract.

**Tech Stack:** Dockerfile 1.x, Docker Compose, Bash, Node.js built-in test runner, VS Code launch/tasks schema, debugpy, pnpm, Vite, FastAPI

---

## File map

- `Dockerfile`: parameterized base images, package mirrors, and runtime timezone installation.
- `scripts/package.sh`: environment-to-build-argument adapter.
- `scripts/project-config.test.mjs`: regression tests for Docker and VS Code configuration contracts.
- `.vscode/extensions.json`: recommended development extensions.
- `.vscode/settings.json`: Python interpreter, analysis, and pytest discovery.
- `.vscode/tasks.json`: macOS fixed-port cleanup tasks.
- `.vscode/launch.json`: FastAPI, Vite, Chrome, and compound configurations.
- `.gitignore`: permits all four shared VS Code files.
- `README.md`: Docker source overrides and VS Code usage.
- `docs/调试标准.md`: stable launch names and debugging sequence.

### Task 1: Add failing Docker configuration tests

**Files:**
- Create: `scripts/project-config.test.mjs`
- Test: `scripts/project-config.test.mjs`

- [ ] **Step 1: Write the Docker build contract test**

Create `scripts/project-config.test.mjs`:

```javascript
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repositoryRoot = join(dirname(fileURLToPath(import.meta.url)), "..");

async function readRepositoryFile(path) {
  return readFile(join(repositoryRoot, path), "utf8");
}

test("Docker build defaults to domestic mirrors and installs the runtime timezone", async () => {
  const dockerfile = await readRepositoryFile("Dockerfile");
  const packageScript = await readRepositoryFile("scripts/package.sh");

  for (const requiredFragment of [
    "ARG NODE_IMAGE=docker.m.daocloud.io/library/node:22-bookworm-slim",
    "ARG PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.11-slim-bookworm",
    "ARG NPM_REGISTRY=https://registry.npmmirror.com",
    "ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/",
    "ARG DEBIAN_MIRROR=mirrors.tuna.tsinghua.edu.cn",
    "ARG TZ=Asia/Shanghai",
    "DEBIAN_FRONTEND=noninteractive",
    "ca-certificates",
    "tzdata",
    "/usr/share/zoneinfo/${TZ}",
    "/etc/timezone",
  ]) {
    assert.ok(dockerfile.includes(requiredFragment), requiredFragment);
  }

  for (const buildArgument of [
    "NODE_IMAGE",
    "PYTHON_IMAGE",
    "NPM_REGISTRY",
    "PIP_INDEX_URL",
    "DEBIAN_MIRROR",
    "TZ",
  ]) {
    const expectedArgument = `--build-arg "${buildArgument}=\${${buildArgument}}"`;
    assert.ok(packageScript.includes(expectedArgument), expectedArgument);
  }
});
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
node --test scripts/project-config.test.mjs
```

Expected: FAIL because the current Dockerfile does not define domestic image/package defaults or install `tzdata`.

### Task 2: Implement Docker mirrors and timezone

**Files:**
- Modify: `Dockerfile`
- Modify: `scripts/package.sh`
- Test: `scripts/project-config.test.mjs`

- [ ] **Step 1: Replace the Dockerfile with the parameterized build**

Use this complete `Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1

# Domestic mirrors are defaults for fast local builds; every value remains
# overridable so CI and international environments can use official sources.
ARG NODE_IMAGE=docker.m.daocloud.io/library/node:22-bookworm-slim
ARG PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.11-slim-bookworm

FROM ${NODE_IMAGE} AS frontend-build
ARG NPM_REGISTRY=https://registry.npmmirror.com
WORKDIR /build/frontend

# npm only bootstraps the project-pinned pnpm version; application dependencies
# continue to be resolved exclusively from pnpm-lock.yaml.
RUN npm install --global "pnpm@10.33.2" --registry="${NPM_REGISTRY}"
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --registry="${NPM_REGISTRY}"
COPY frontend/ ./
COPY VERSION /build/VERSION
RUN pnpm build

FROM ${PYTHON_IMAGE} AS runtime
ARG DEBIAN_MIRROR=mirrors.tuna.tsinghua.edu.cn
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG TZ=Asia/Shanghai
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend \
    TZ=${TZ}

# Debian slim variants may use either legacy sources.list or deb822 sources.
# Update both forms before installing timezone data, then remove apt metadata.
RUN set -eux; \
    if [ -f /etc/apt/sources.list ]; then \
      sed -i \
        -e "s|deb.debian.org|${DEBIAN_MIRROR}|g" \
        -e "s|security.debian.org|${DEBIAN_MIRROR}|g" \
        /etc/apt/sources.list; \
    fi; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i \
        -e "s|deb.debian.org|${DEBIAN_MIRROR}|g" \
        -e "s|security.debian.org|${DEBIAN_MIRROR}|g" \
        /etc/apt/sources.list.d/debian.sources; \
    fi; \
    DEBIAN_FRONTEND=noninteractive apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ca-certificates \
      tzdata; \
    ln -snf "/usr/share/zoneinfo/${TZ}" /etc/localtime; \
    printf '%s\n' "${TZ}" > /etc/timezone; \
    test -e /etc/localtime; \
    test "$(cat /etc/timezone)" = "${TZ}"; \
    rm -rf /var/lib/apt/lists/*

COPY VERSION /app/VERSION
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" \
    -r /app/backend/requirements.txt
COPY backend/app/ /app/backend/app/
COPY --from=frontend-build /build/frontend/dist /app/static/

RUN mkdir -p /app/data
VOLUME ["/app/data"]
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Forward source settings from the package script**

Replace `scripts/package.sh` with:

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

NODE_IMAGE="${NODE_IMAGE:-docker.m.daocloud.io/library/node:22-bookworm-slim}"
PYTHON_IMAGE="${PYTHON_IMAGE:-docker.m.daocloud.io/library/python:3.11-slim-bookworm}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmmirror.com}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}"
DEBIAN_MIRROR="${DEBIAN_MIRROR:-mirrors.tuna.tsinghua.edu.cn}"
TZ="${TZ:-Asia/Shanghai}"

corepack pnpm --dir "${ROOT}/frontend" install --frozen-lockfile
corepack pnpm --dir "${ROOT}/frontend" build
docker build \
  --build-arg "NODE_IMAGE=${NODE_IMAGE}" \
  --build-arg "PYTHON_IMAGE=${PYTHON_IMAGE}" \
  --build-arg "NPM_REGISTRY=${NPM_REGISTRY}" \
  --build-arg "PIP_INDEX_URL=${PIP_INDEX_URL}" \
  --build-arg "DEBIAN_MIRROR=${DEBIAN_MIRROR}" \
  --build-arg "TZ=${TZ}" \
  -f "${ROOT}/Dockerfile" \
  -t genstack:latest \
  "${ROOT}"
```

- [ ] **Step 3: Run Docker configuration checks**

Run:

```bash
node --test scripts/project-config.test.mjs
bash -n scripts/package.sh
```

Expected: one Node test passes and Bash syntax validation succeeds.

- [ ] **Step 4: Commit Docker changes**

```bash
git add Dockerfile scripts/package.sh scripts/project-config.test.mjs
git commit -m "build: add domestic Docker mirrors and timezone"
```

### Task 3: Add failing VS Code configuration test

**Files:**
- Modify: `scripts/project-config.test.mjs`
- Test: `scripts/project-config.test.mjs`

- [ ] **Step 1: Add the VS Code contract test**

Append to `scripts/project-config.test.mjs`:

```javascript
test("VS Code exposes backend, frontend, browser, and full-stack launches", async () => {
  const extensions = JSON.parse(await readRepositoryFile(".vscode/extensions.json"));
  const settings = JSON.parse(await readRepositoryFile(".vscode/settings.json"));
  const tasks = JSON.parse(await readRepositoryFile(".vscode/tasks.json"));
  const launch = JSON.parse(await readRepositoryFile(".vscode/launch.json"));

  assert.deepEqual(
    new Set(extensions.recommendations),
    new Set([
      "ms-python.python",
      "ms-python.debugpy",
      "bradlc.vscode-tailwindcss",
      "oxc.oxc-vscode",
      "ms-azuretools.vscode-docker",
    ]),
  );
  assert.equal(
    settings["python.defaultInterpreterPath"],
    "${workspaceFolder}/backend/.venv/bin/python",
  );
  assert.equal(settings["python.testing.pytestEnabled"], true);

  assert.deepEqual(
    tasks.tasks.map(({ label }) => label),
    ["debug: kill backend port 8000", "debug: kill frontend port 5173"],
  );
  assert.deepEqual(
    launch.configurations.map(({ name }) => name),
    [
      "Python: FastAPI (后端)",
      "Python: FastAPI (后端, 热重载)",
      "pnpm: 前端开发 (Vite)",
      "Chrome: 前端页面",
    ],
  );
  assert.deepEqual(launch.compounds[0].configurations, [
    "Python: FastAPI (后端)",
    "pnpm: 前端开发 (Vite)",
  ]);
  assert.equal(launch.compounds[0].stopAll, true);
});
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
node --test scripts/project-config.test.mjs
```

Expected: Docker test passes; VS Code test fails with `ENOENT` for `.vscode/extensions.json`.

### Task 4: Implement VS Code runtime configuration

**Files:**
- Create: `.vscode/extensions.json`
- Create: `.vscode/settings.json`
- Create: `.vscode/tasks.json`
- Create: `.vscode/launch.json`
- Modify: `.gitignore`
- Test: `scripts/project-config.test.mjs`

- [ ] **Step 1: Add recommended extensions**

Create `.vscode/extensions.json`:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.debugpy",
    "bradlc.vscode-tailwindcss",
    "oxc.oxc-vscode",
    "ms-azuretools.vscode-docker"
  ]
}
```

- [ ] **Step 2: Add Python workspace settings**

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/bin/python",
  "python.analysis.extraPaths": ["${workspaceFolder}/backend"],
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["backend/tests"],
  "python.testing.cwd": "${workspaceFolder}"
}
```

- [ ] **Step 3: Add macOS port cleanup tasks**

Create `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "debug: kill backend port 8000",
      "type": "shell",
      "command": "bash",
      "args": [
        "-lc",
        "pids=$(lsof -tiTCP:8000 -sTCP:LISTEN || true); if [ -n \"$pids\" ]; then kill -9 $pids; echo \"Stopped port 8000 listeners: $pids\"; else echo \"Port 8000 is free\"; fi"
      ],
      "problemMatcher": [],
      "presentation": {
        "reveal": "always",
        "panel": "dedicated",
        "focus": false
      }
    },
    {
      "label": "debug: kill frontend port 5173",
      "type": "shell",
      "command": "bash",
      "args": [
        "-lc",
        "pids=$(lsof -tiTCP:5173 -sTCP:LISTEN || true); if [ -n \"$pids\" ]; then kill -9 $pids; echo \"Stopped port 5173 listeners: $pids\"; else echo \"Port 5173 is free\"; fi"
      ],
      "problemMatcher": [],
      "presentation": {
        "reveal": "always",
        "panel": "dedicated",
        "focus": false
      }
    }
  ]
}
```

- [ ] **Step 4: Add launch and compound configurations**

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI (后端)",
      "type": "debugpy",
      "request": "launch",
      "preLaunchTask": "debug: kill backend port 8000",
      "module": "uvicorn",
      "args": ["app.main:app", "--host", "127.0.0.1", "--port", "8000"],
      "cwd": "${workspaceFolder}/backend",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/backend"
      },
      "console": "integratedTerminal",
      "justMyCode": true
    },
    {
      "name": "Python: FastAPI (后端, 热重载)",
      "type": "debugpy",
      "request": "launch",
      "preLaunchTask": "debug: kill backend port 8000",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
      "cwd": "${workspaceFolder}/backend",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/backend"
      },
      "console": "integratedTerminal",
      "justMyCode": true
    },
    {
      "name": "pnpm: 前端开发 (Vite)",
      "type": "node-terminal",
      "request": "launch",
      "preLaunchTask": "debug: kill frontend port 5173",
      "command": "corepack pnpm dev",
      "cwd": "${workspaceFolder}/frontend"
    },
    {
      "name": "Chrome: 前端页面",
      "type": "chrome",
      "request": "launch",
      "url": "http://127.0.0.1:5173",
      "webRoot": "${workspaceFolder}/frontend",
      "sourceMaps": true
    }
  ],
  "compounds": [
    {
      "name": "全栈: 后端调试 + Vite",
      "configurations": ["Python: FastAPI (后端)", "pnpm: 前端开发 (Vite)"],
      "stopAll": true,
      "presentation": {
        "group": "fullstack",
        "order": 1
      }
    }
  ]
}
```

- [ ] **Step 5: Track the workspace settings**

Add this line beneath the existing `.vscode` exceptions in `.gitignore`:

```gitignore
!.vscode/settings.json
```

- [ ] **Step 6: Run VS Code configuration tests**

Run:

```bash
node --test scripts/project-config.test.mjs
node -e 'for (const file of [".vscode/extensions.json", ".vscode/settings.json", ".vscode/tasks.json", ".vscode/launch.json"]) JSON.parse(require("node:fs").readFileSync(file, "utf8"))'
bash -lc 'pids=$(lsof -tiTCP:8000 -sTCP:LISTEN || true); if [ -n "$pids" ]; then exit 1; else echo "Port 8000 is free"; fi'
bash -lc 'pids=$(lsof -tiTCP:5173 -sTCP:LISTEN || true); if [ -n "$pids" ]; then exit 1; else echo "Port 5173 is free"; fi'
```

Expected: two Node tests pass, JSON parsing succeeds, and both unused-port checks print `is free`.

- [ ] **Step 7: Commit VS Code configuration**

```bash
git add .gitignore .vscode scripts/project-config.test.mjs
git commit -m "chore: add VS Code full-stack launch configuration"
```

### Task 5: Document Docker and VS Code usage

**Files:**
- Modify: `README.md`
- Modify: `docs/调试标准.md`

- [ ] **Step 1: Expand the Docker section in README**

Replace the current Docker section with:

````markdown
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
````

- [ ] **Step 2: Add the VS Code README section**

Insert before `## 文档`:

```markdown
## VS Code

首次使用前完成本地依赖安装，然后接受工作区推荐扩展。运行和调试面板提供：

- `Python: FastAPI (后端)`：稳定断点调试；
- `Python: FastAPI (后端, 热重载)`：后端热更新；
- `pnpm: 前端开发 (Vite)`：启动 React 开发服务器；
- `Chrome: 前端页面`：连接前端源码调试；
- `全栈: 后端调试 + Vite`：同时启动前后端。

启动配置会先清理固定端口 `8000` 或 `5173`。Chrome 配置应在 Vite 就绪后单独启动，
避免浏览器和开发服务器启动竞态。
```

- [ ] **Step 3: Replace the debugging standard**

Use this complete `docs/调试标准.md`:

````markdown
# 调试标准

后端固定使用 `127.0.0.1:8000`，前端固定使用 `127.0.0.1:5173`。端口被占用时
应查找并结束旧进程，不通过更换端口规避。

## VS Code

运行和调试面板提供以下配置：

- `Python: FastAPI (后端)`：无热重载，断点行为最稳定；
- `Python: FastAPI (后端, 热重载)`：代码变更后自动重启；
- `pnpm: 前端开发 (Vite)`：通过 pnpm 启动 Vite；
- `Chrome: 前端页面`：在 Vite 就绪后启动浏览器源码调试；
- `全栈: 后端调试 + Vite`：同时启动后端普通调试和 Vite。

前端与后端启动前分别执行 macOS 端口清理任务。任务在端口空闲时正常成功，不会通过
修改端口绕过冲突。

## 排查顺序

1. 请求 `http://127.0.0.1:8000/api/health`；
2. 检查 `.env` 与后端启动日志；
3. 检查 Vite `/api` 代理；
4. 检查浏览器请求和前端状态。

## 验证命令

```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -q
corepack pnpm --dir frontend check
node --test scripts/project-config.test.mjs
docker compose config --quiet
```
````

- [ ] **Step 4: Commit documentation**

```bash
git add README.md docs/调试标准.md
git commit -m "docs: explain Docker mirrors and VS Code debugging"
```

### Task 6: Final validation and audit

**Files:**
- Inspect: all changed files
- Modify: only files that fail checks or contain stale comments/documentation

- [ ] **Step 1: Run configuration and application checks**

```bash
node --test scripts/project-config.test.mjs
bash -n scripts/*.sh
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -q
corepack pnpm --dir frontend check
ruby -e 'require "yaml"; config = YAML.safe_load(File.read("docker-compose.yml")); abort "missing app service" unless config.dig("services", "app")'
```

Expected: two configuration tests, two backend tests, three frontend tests, lint, typecheck,
build, Shell syntax, and Compose YAML parsing all pass.

- [ ] **Step 2: Audit comments, docs, and stale stack references**

```bash
git diff origin/main --check
rg -n "vue|shadcn-vue|package-lock|npm run dev|APP_HOST|APP_PORT" \
  .vscode Dockerfile scripts README.md docs/调试标准.md
git status --short
```

Expected: no whitespace errors or stale Vue/npm/server-setting references. `npm install`
inside Dockerfile is allowed only for bootstrapping pnpm through the configured registry.

- [ ] **Step 3: Record the Docker environment limitation**

If `docker` is unavailable, add this implementation note to the design document:

```markdown
- Local static validation passed, but Docker image construction and container timezone
  inspection were not run because the host has no Docker CLI.
```

If Docker is available, run:

```bash
bash scripts/package.sh
docker run --rm --entrypoint sh genstack:latest -c \
  'test "$(cat /etc/timezone)" = "Asia/Shanghai" && test -e /etc/localtime'
docker run --rm -d --name genstack-smoke -p 8000:8000 genstack:latest
curl --fail --silent http://127.0.0.1:8000/api/health
docker rm -f genstack-smoke
```

Expected: image build succeeds, timezone checks pass, and health returns `{"status":"ok"}`.

- [ ] **Step 4: Commit final corrections if necessary**

```bash
git add -A
git commit -m "chore: finalize Docker and VS Code configuration"
```

Expected: skip this commit when the working tree is already clean.
