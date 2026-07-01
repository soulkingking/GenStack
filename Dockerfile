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
