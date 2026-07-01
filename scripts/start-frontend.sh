#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec corepack pnpm --dir "${ROOT}/frontend" dev
