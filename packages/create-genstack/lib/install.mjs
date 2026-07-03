// 跨平台安装前后端依赖：优先 uv，回退系统 Python；前端经 corepack pnpm。
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import process from "node:process";

const isWindows = process.platform === "win32";

export const venvBinDir = isWindows ? "Scripts" : "bin";

function commandExists(command) {
  const probe = spawnSync(command, ["--version"], { stdio: "ignore", shell: isWindows });
  return probe.error?.code !== "ENOENT" && probe.status === 0;
}

function run(command, args) {
  const result = spawnSync(command, args, { stdio: "inherit" });
  return result.error == null && result.status === 0;
}

// corepack 在 Windows 上是 .cmd 垫片，Node 出于安全限制必须经 shell 调用；
// 统一自行加引号拼接，避免路径含空格时被 shell 拆分。
function runCorepack(args) {
  if (!isWindows) {
    return run("corepack", args);
  }
  const command = ["corepack", ...args].map((part) => `"${part}"`).join(" ");
  const result = spawnSync(command, { stdio: "inherit", shell: true });
  return result.error == null && result.status === 0;
}

function createVenvWithPython(target) {
  const candidates = isWindows
    ? [
        ["py", ["-3.11", "-m", "venv", join(target, "backend", ".venv")]],
        ["python", ["-m", "venv", join(target, "backend", ".venv")]],
      ]
    : [["python3.11", ["-m", "venv", join(target, "backend", ".venv")]]];
  return candidates.some(([command, args]) => commandExists(command) && run(command, args));
}

function installBackend(target) {
  const venvPython = join(
    target,
    "backend",
    ".venv",
    venvBinDir,
    isWindows ? "python.exe" : "python",
  );
  const requirements = join(target, "backend", "requirements-dev.txt");

  if (commandExists("uv")) {
    return (
      run("uv", ["venv", "--python", "3.11", "--seed", join(target, "backend", ".venv")]) &&
      run("uv", ["pip", "install", "--python", venvPython, "-r", requirements])
    );
  }
  if (!createVenvWithPython(target)) {
    process.stderr.write("警告: 未找到 uv 或 Python 3.11，无法创建后端虚拟环境。\n");
    return false;
  }
  return run(venvPython, ["-m", "pip", "install", "-r", requirements]);
}

function installFrontend(target) {
  if (!commandExists("corepack")) {
    process.stderr.write("警告: 未找到 corepack（需 Node.js >= 22），无法安装前端依赖。\n");
    return false;
  }
  return runCorepack([
    "pnpm",
    "--dir",
    join(target, "frontend"),
    "install",
    "--frozen-lockfile",
  ]);
}

export function installDependencies(target) {
  process.stdout.write("[1/2] 安装后端依赖 ...\n");
  if (!installBackend(target)) {
    return false;
  }
  process.stdout.write("[2/2] 安装前端依赖 ...\n");
  return installFrontend(target);
}

export function manualInstallSteps(target) {
  const pip = join("backend", ".venv", venvBinDir, "pip");
  return [
    "",
    `  cd ${target}`,
    "  uv venv --python 3.11 --seed backend/.venv   # 后端虚拟环境（或 python -m venv）",
    `  ${pip} install -r backend/requirements-dev.txt`,
    "  node scripts/init-frontend.mjs               # 前端依赖（corepack pnpm 按锁文件安装）",
    "",
  ].join("\n");
}
