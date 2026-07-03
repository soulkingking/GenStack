#!/usr/bin/env node
// 从 GenStack 模板创建新项目：克隆模板仓库到临时目录，
// 再委托模板内的 scripts/create-project.sh 完成复制、改名和 git 初始化。
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import process from "node:process";

const DEFAULT_REPO = "https://github.com/soulkingking/GenStack.git";

const USAGE = `用法: npm create genstack@latest -- <project-name> [target-dir] [选项]
   或: npx create-genstack <project-name> [target-dir] [选项]

  project-name     小写字母开头，仅含小写字母、数字和连字符（如 my-app）
  target-dir       目标目录，默认为当前目录下的 <project-name>/

选项:
  --repo <url>     模板仓库地址（默认 ${DEFAULT_REPO}）
  --ref <ref>      模板分支或标签（默认 main）
  --skip-install   只生成项目，跳过前后端依赖安装
  -h, --help       显示帮助
`;

function parseArgs(argv) {
  const options = { repo: DEFAULT_REPO, ref: "main", skipInstall: false, positional: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "-h" || arg === "--help") {
      return { ...options, help: true };
    }
    if (arg === "--skip-install") {
      options.skipInstall = true;
    } else if (arg === "--repo" || arg === "--ref") {
      const value = argv[i + 1];
      if (!value) {
        throw new Error(`选项 ${arg} 缺少参数值`);
      }
      i += 1;
      options[arg.slice(2)] = value;
    } else if (arg.startsWith("-")) {
      throw new Error(`未知选项: ${arg}`);
    } else {
      options.positional = [...options.positional, arg];
    }
  }
  return options;
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, { stdio: "inherit", ...options });
  if (result.error?.code === "ENOENT") {
    throw new Error(`未找到命令 ${command}，请先安装（Windows 建议在 Git Bash 中执行）`);
  }
  if (result.status !== 0) {
    throw new Error(`${command} ${args[0]} 执行失败（退出码 ${result.status}）`);
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    process.stdout.write(USAGE);
    return 0;
  }

  const [name, targetArg, ...rest] = options.positional;
  if (!name || rest.length > 0) {
    process.stderr.write(USAGE);
    return 1;
  }
  if (!/^[a-z][a-z0-9-]*$/.test(name)) {
    process.stderr.write(`错误: 项目名 '${name}' 不合法。\n${USAGE}`);
    return 1;
  }
  const target = resolve(process.cwd(), targetArg ?? name);

  const cloneDir = mkdtempSync(join(tmpdir(), "create-genstack-"));
  try {
    process.stdout.write(`克隆模板 ${options.repo} (${options.ref}) ...\n`);
    run("git", [
      "clone",
      "--quiet",
      "--depth",
      "1",
      "--branch",
      options.ref,
      options.repo,
      join(cloneDir, "template"),
    ]);
    const scriptArgs = [join(cloneDir, "template", "scripts", "create-project.sh"), name, target];
    run("bash", options.skipInstall ? [...scriptArgs, "--skip-install"] : scriptArgs);
  } finally {
    rmSync(cloneDir, { recursive: true, force: true });
  }
  return 0;
}

try {
  process.exit(main());
} catch (error) {
  process.stderr.write(`错误: ${error.message}\n`);
  process.exit(1);
}
