#!/usr/bin/env bash
set -euo pipefail

# 从 GenStack 模板生成新项目：复制受版本管理的文件、替换项目标识、
# 重置版本与变更记录，并初始化全新的 git 仓库。
#
# 本地没有模板时可直接远程执行（自举模式会先克隆模板再继续）：
#   curl -fsSL https://raw.githubusercontent.com/soulkingking/GenStack/main/scripts/create-project.sh \
#     | bash -s -- <project-name> [target-dir]

TEMPLATE_REPO="${GENSTACK_REPO:-https://github.com/soulkingking/GenStack.git}"
TEMPLATE_REF="${GENSTACK_REF:-main}"

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

usage() {
  cat >&2 <<'EOF'
用法: bash scripts/create-project.sh <project-name> [target-dir]

  project-name  新项目名，小写字母开头，仅含小写字母、数字和连字符（如 my-app）。
                同时用作 Docker 镜像名、Compose 项目名、pnpm scope 和 Nacos 服务名；
                显示名按 PascalCase 派生（my-app -> MyApp）。
  target-dir    目标目录，默认为当前目录下的 <project-name>/，要求不存在。
EOF
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 1
fi

NAME="$1"
if [[ ! "$NAME" =~ ^[a-z][a-z0-9-]*$ ]]; then
  echo "错误: 项目名 '${NAME}' 不合法。" >&2
  usage
  exit 1
fi

ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
TARGET="${2:-${PWD}/${NAME}}"
case "$TARGET" in
  /*) ;;
  *) TARGET="${PWD}/${TARGET}" ;;
esac

if [[ -e "$TARGET" ]]; then
  echo "错误: 目标目录已存在: ${TARGET}" >&2
  exit 1
fi
case "$TARGET" in
  "$ROOT"/*)
    echo "错误: 目标目录不能位于模板仓库内部: ${TARGET}" >&2
    exit 1
    ;;
esac
if ! git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "错误: 模板目录不是 git 仓库，无法确定要复制的文件: ${ROOT}" >&2
  exit 1
fi

# my-app -> MyApp
DISPLAY="$(printf '%s' "$NAME" | awk -F- '{ for (i = 1; i <= NF; i++) printf "%s%s", toupper(substr($i, 1, 1)), substr($i, 2) }')"

echo "创建项目 ${DISPLAY} (${NAME}) -> ${TARGET}"
mkdir -p "$TARGET"

# 复制受版本管理的文件（含未忽略的新文件），自动跳过 .git、依赖和构建产物。
git -C "$ROOT" ls-files -z --cached --others --exclude-standard \
  | tar -C "$ROOT" --null -T - -cf - \
  | tar -C "$TARGET" -xf -

# 脚手架自身（本脚本、CLI、skill）与模板的开发文档、发布记录不属于新项目。
rm -rf "$TARGET/docs/superpowers" "$TARGET/release-notes" "$TARGET/packages" \
  "$TARGET/.claude/skills/genstack" "$TARGET/scripts/create-project.sh"

# 剥离文档中标记为「仅模板需要」的段落。
grep -rIlF 'template-only:start' "$TARGET" | while IFS= read -r file; do
  perl -0777 -pi -e 's/[ \t]*<!-- template-only:start -->.*?<!-- template-only:end -->\n*//gs' "$file"
done

# 替换项目标识：GenStack -> 显示名，genstack -> slug（仅处理文本文件）。
grep -rIl -e genstack -e GenStack "$TARGET" | while IFS= read -r file; do
  perl -pi -e "s/genstack/${NAME}/g; s/GenStack/${DISPLAY}/g" "$file"
done

printf '0.1.0\n' >"$TARGET/VERSION"
cat >"$TARGET/CHANGELOG.md" <<EOF
# Changelog

## 0.1.0

- 基于 GenStack 模板初始化 ${DISPLAY}。
EOF
cp "$TARGET/.env.example" "$TARGET/.env"

if git -C "$TARGET" init -b main -q && git -C "$TARGET" add -A \
  && git -C "$TARGET" commit -q -m "chore: initialize ${NAME} from GenStack template"; then
  echo "已初始化 git 仓库并完成首次提交。"
else
  echo "警告: git 初始化或首次提交失败，请手动处理。" >&2
fi

cat <<EOF

完成。后续步骤（需 Python 3.11 与 Node.js >= 22）:

  cd ${TARGET}
  uv venv --python 3.11 --seed backend/.venv                     # 后端虚拟环境
  backend/.venv/bin/pip install -r backend/requirements-dev.txt  # 后端依赖
  bash scripts/init-frontend.sh                                  # 前端依赖（corepack pnpm 按锁文件安装）
  bash scripts/start-backend.sh   # 另开终端: bash scripts/start-frontend.sh

请检查 README.md 的项目描述和 .env 中的 Nacos / 认证配置。
EOF
