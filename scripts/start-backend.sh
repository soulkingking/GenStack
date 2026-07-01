#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${ROOT}/backend"
UVICORN=(uvicorn)
if [[ -x "${ROOT}/backend/.venv/bin/uvicorn" ]]; then
  UVICORN=("${ROOT}/backend/.venv/bin/uvicorn")
fi
cd "${ROOT}/backend"
exec "${UVICORN[@]}" app.main:app --reload --host 127.0.0.1 --port 8000
