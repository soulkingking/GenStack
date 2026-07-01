#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
corepack pnpm --dir "${ROOT}/frontend" install --frozen-lockfile
corepack pnpm --dir "${ROOT}/frontend" build
docker build -f "${ROOT}/Dockerfile" -t genstack:latest "${ROOT}"
