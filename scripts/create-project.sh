#!/usr/bin/env bash
set -euo pipefail

# unix 入口：从 GenStack 模板生成新项目。实际逻辑位于
# packages/create-genstack（纯 Node，跨平台），本脚本仅负责
# curl | bash 自举与本地委托。Windows 请直接使用:
#   npm create genstack@latest -- <project-name>
#
# 本地没有模板时可直接远程执行:
#   curl -fsSL https://raw.githubusercontent.com/soulkingking/GenStack/main/scripts/create-project.sh \
#     | bash -s -- <project-name> [target-dir] [--skip-install]

TEMPLATE_REPO="${GENSTACK_REPO:-https://github.com/soulkingking/GenStack.git}"
TEMPLATE_REF="${GENSTACK_REF:-main}"

if ! command -v node >/dev/null 2>&1; then
  echo "错误: 需要 Node.js >= 18，请先安装。" >&2
  exit 1
fi

SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"
if [[ ! -f "$SCRIPT_PATH" ]]; then
  # 通过 curl | bash 等管道执行，本地没有模板：克隆到临时目录后重新执行。
  CLONE_DIR="$(mktemp -d)"
  trap 'rm -rf "$CLONE_DIR"' EXIT
  echo "本地未找到模板，克隆 ${TEMPLATE_REPO} (${TEMPLATE_REF}) ..."
  git clone --quiet --depth 1 --branch "$TEMPLATE_REF" "$TEMPLATE_REPO" "$CLONE_DIR/template"
  bash "$CLONE_DIR/template/scripts/create-project.sh" "$@"
  exit 0
fi

ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
exec node "$ROOT/packages/create-genstack/bin/create-genstack.mjs" --template "$ROOT" "$@"
