// 开发脚本共用的跨平台进程辅助函数。
import { spawnSync } from "node:child_process";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import process from "node:process";

export const isWindows = process.platform === "win32";

// 仓库根目录（本文件位于 scripts/lib/ 下）。
export const repositoryRoot = dirname(dirname(dirname(fileURLToPath(import.meta.url))));

export function run(command, args, options = {}) {
  const result = spawnSync(command, args, { stdio: "inherit", ...options });
  if (result.error?.code === "ENOENT") {
    process.stderr.write(`错误: 未找到命令 ${command}，请先安装。\n`);
    process.exit(1);
  }
  return result.status ?? 1;
}

// corepack 在 Windows 上是 .cmd 垫片，Node 出于安全限制必须经 shell 调用；
// 自行加引号拼接，避免路径含空格时被 shell 拆分。
export function runPnpm(args, options = {}) {
  if (!isWindows) {
    return run("corepack", ["pnpm", ...args], options);
  }
  const command = ["corepack", "pnpm", ...args].map((part) => `"${part}"`).join(" ");
  const result = spawnSync(command, { stdio: "inherit", shell: true, ...options });
  if (result.error) {
    process.stderr.write("错误: 未找到命令 corepack（需 Node.js >= 22）。\n");
    process.exit(1);
  }
  return result.status ?? 1;
}
