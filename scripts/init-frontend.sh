#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# 固定使用锁文件安装，避免不同开发环境解析出不同依赖版本。
exec corepack pnpm --dir "${ROOT}/frontend" install --frozen-lockfile
