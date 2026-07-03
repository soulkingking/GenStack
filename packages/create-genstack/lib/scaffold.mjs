// 从模板目录生成新项目：复制受版本管理的文件、剥离模板专用内容、
// 替换项目标识、重置版本并初始化 git 仓库。纯 Node 实现，跨平台。
import { spawnSync } from "node:child_process";
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { dirname, isAbsolute, join, relative } from "node:path";

// 脚手架自身与模板的开发文档、发布记录不属于新项目。
const EXCLUDED_PREFIXES = [
  "docs/superpowers/",
  "release-notes/",
  "packages/",
  ".claude/skills/genstack/",
];
const EXCLUDED_FILES = new Set(["scripts/create-project.sh"]);
const TEMPLATE_ONLY_PATTERN = /[ \t]*<!-- template-only:start -->[\s\S]*?<!-- template-only:end -->\n*/g;

export function isValidProjectName(name) {
  return /^[a-z][a-z0-9-]*$/.test(name);
}

// my-app -> MyApp
export function toDisplayName(name) {
  return name
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join("");
}

function runGit(args, errorMessage) {
  const result = spawnSync("git", args, { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  if (result.error?.code === "ENOENT") {
    throw new Error("未找到命令 git，请先安装（Windows 可安装 Git for Windows）");
  }
  if (result.status !== 0) {
    throw new Error(`${errorMessage}\n${(result.stderr ?? "").trim()}`);
  }
  return result.stdout;
}

// 受版本管理的文件（含未忽略的新文件），git 输出统一使用正斜杠路径。
function listTemplateFiles(templateDir) {
  const stdout = runGit(
    ["-C", templateDir, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
    `无法列出模板文件，请确认模板目录是 git 仓库: ${templateDir}`,
  );
  return stdout
    .split("\0")
    .filter(Boolean)
    .filter(
      (file) =>
        !EXCLUDED_PREFIXES.some((prefix) => file.startsWith(prefix)) &&
        !EXCLUDED_FILES.has(file),
    );
}

function copyTemplateFiles(templateDir, target, files) {
  return files.filter((file) => {
    const source = join(templateDir, file);
    if (!existsSync(source)) {
      return false;
    }
    const destination = join(target, file);
    mkdirSync(dirname(destination), { recursive: true });
    copyFileSync(source, destination);
    return true;
  });
}

// 剥离「仅模板需要」段落并替换项目标识；二进制文件（含 NUL 字节）跳过。
function rewriteIdentity(target, files, name, display) {
  for (const file of files) {
    const path = join(target, file);
    const buffer = readFileSync(path);
    if (buffer.includes(0)) {
      continue;
    }
    const text = buffer.toString("utf8");
    const rewritten = text
      .replace(TEMPLATE_ONLY_PATTERN, "")
      .replaceAll("genstack", name)
      .replaceAll("GenStack", display);
    if (rewritten !== text) {
      const mode = statSync(path).mode;
      writeFileSync(path, rewritten, { mode });
    }
  }
}

function resetProjectFiles(target, display) {
  writeFileSync(join(target, "VERSION"), "0.1.0\n");
  writeFileSync(
    join(target, "CHANGELOG.md"),
    `# Changelog\n\n## 0.1.0\n\n- 基于 GenStack 模板初始化 ${display}。\n`,
  );
  copyFileSync(join(target, ".env.example"), join(target, ".env"));
}

function initGitRepository(target, name) {
  const steps = [
    ["-C", target, "init", "-b", "main", "-q"],
    ["-C", target, "add", "-A"],
    ["-C", target, "commit", "-q", "-m", `chore: initialize ${name} from GenStack template`],
  ];
  for (const args of steps) {
    const result = spawnSync("git", args, { stdio: "inherit" });
    if (result.status !== 0) {
      process.stderr.write("警告: git 初始化或首次提交失败，请手动处理。\n");
      return;
    }
  }
  process.stdout.write("已初始化 git 仓库并完成首次提交。\n");
}

export function assertValidTarget(target, templateDir) {
  if (existsSync(target)) {
    throw new Error(`目标目录已存在: ${target}`);
  }
  const relativePath = relative(templateDir, target);
  if (relativePath === "" || (!relativePath.startsWith("..") && !isAbsolute(relativePath))) {
    throw new Error(`目标目录不能位于模板仓库内部: ${target}`);
  }
}

export function scaffold({ templateDir, target, name }) {
  const display = toDisplayName(name);
  process.stdout.write(`创建项目 ${display} (${name}) -> ${target}\n`);

  const files = listTemplateFiles(templateDir);
  const copied = copyTemplateFiles(templateDir, target, files);
  rewriteIdentity(target, copied, name, display);
  resetProjectFiles(target, display);
  initGitRepository(target, name);
  return { display };
}
