#!/usr/bin/env node
// 从 GenStack 模板创建新项目：克隆模板仓库（或使用 --template 指定的本地模板），
// 复制文件、替换项目标识、初始化 git 并安装依赖。纯 Node 实现，macOS/Linux/Windows 通用。
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import process from "node:process";

import { installDependencies, manualInstallSteps } from "../lib/install.mjs";
import { assertValidTarget, isValidProjectName, scaffold } from "../lib/scaffold.mjs";

const DEFAULT_REPO = "https://github.com/soulkingking/GenStack.git";

const USAGE = `用法: npm create genstack@latest -- <project-name> [target-dir] [选项]
   或: npx create-genstack <project-name> [target-dir] [选项]

  project-name     小写字母开头，仅含小写字母、数字和连字符（如 my-app）
  target-dir       目标目录，默认为当前目录下的 <project-name>/

选项:
  --repo <url>     模板仓库地址（默认 ${DEFAULT_REPO}）
  --ref <ref>      模板分支或标签（默认 main）
  --template <dir> 使用本地模板目录，跳过克隆
  --skip-install   只生成项目，跳过前后端依赖安装
  -h, --help       显示帮助
`;

function parseArgs(argv) {
  const options = {
    repo: DEFAULT_REPO,
    ref: "main",
    template: null,
    skipInstall: false,
    positional: [],
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "-h" || arg === "--help") {
      return { ...options, help: true };
    }
    if (arg === "--skip-install") {
      options.skipInstall = true;
    } else if (arg === "--repo" || arg === "--ref" || arg === "--template") {
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

function cloneTemplate(repo, ref, cloneDir) {
  process.stdout.write(`克隆模板 ${repo} (${ref}) ...\n`);
  const result = spawnSync(
    "git",
    ["clone", "--quiet", "--depth", "1", "--branch", ref, repo, cloneDir],
    { stdio: "inherit" },
  );
  if (result.error?.code === "ENOENT") {
    throw new Error("未找到命令 git，请先安装（Windows 可安装 Git for Windows）");
  }
  if (result.status !== 0) {
    throw new Error(`克隆模板失败（退出码 ${result.status}）`);
  }
}

function printNextSteps(target, installed, skipped) {
  if (skipped) {
    process.stdout.write("完成（已跳过依赖安装）。手动安装（需 Python >= 3.11 与 Node.js >= 22）:\n");
    process.stdout.write(`${manualInstallSteps(target)}\n`);
  } else if (installed) {
    process.stdout.write("完成，前后端依赖已安装。\n");
  } else {
    process.stderr.write("完成，但依赖安装未成功，请手动执行（需 Python >= 3.11 与 Node.js >= 22）:\n");
    process.stdout.write(`${manualInstallSteps(target)}\n`);
  }
  process.stdout.write(`
启动开发服务器:

  cd ${target}
  node scripts/start-backend.mjs   # 另开终端: node scripts/start-frontend.mjs

也可在 VS Code 中直接 F5 调试（配置见 .vscode/launch.json）。
请检查 README.md 的项目描述和 .env 中的 Nacos / 认证配置。
`);
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
  if (!isValidProjectName(name)) {
    process.stderr.write(`错误: 项目名 '${name}' 不合法。\n${USAGE}`);
    return 1;
  }
  const target = resolve(process.cwd(), targetArg ?? name);

  if (options.template) {
    const templateDir = resolve(process.cwd(), options.template);
    assertValidTarget(target, templateDir);
    scaffold({ templateDir, target, name });
  } else {
    const cloneRoot = mkdtempSync(join(tmpdir(), "create-genstack-"));
    try {
      const templateDir = join(cloneRoot, "template");
      cloneTemplate(options.repo, options.ref, templateDir);
      assertValidTarget(target, templateDir);
      scaffold({ templateDir, target, name });
    } finally {
      rmSync(cloneRoot, { recursive: true, force: true });
    }
  }

  const installed = options.skipInstall ? false : installDependencies(target);
  printNextSteps(target, installed, options.skipInstall);
  return 0;
}

try {
  process.exit(main());
} catch (error) {
  process.stderr.write(`错误: ${error.message}\n`);
  process.exit(1);
}
