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
