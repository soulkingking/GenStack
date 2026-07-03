// 跨平台安装前后端依赖：优先 uv，回退系统 Python 3.11；前端经 corepack pnpm。
// 与模板 Dockerfile 保持一致，默认使用国内镜像源，可通过同名环境变量覆盖。
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import process from "node:process";

const isWindows = process.platform === "win32";

const PIP_INDEX_URL = process.env.PIP_INDEX_URL ?? "https://mirrors.aliyun.com/pypi/simple/";
const NPM_REGISTRY = process.env.NPM_REGISTRY ?? "https://registry.npmmirror.com";
const REQUIRED_PYTHON = "3.11";

export const venvBinDir = isWindows ? "Scripts" : "bin";

function commandExists(command) {
  const probe = spawnSync(command, ["--version"], { stdio: "ignore", shell: isWindows });
  return probe.error?.code !== "ENOENT" && probe.status === 0;
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, { stdio: "inherit", ...options });
  return result.error == null && result.status === 0;
}

// corepack 在 Windows 上是 .cmd 垫片，Node 出于安全限制必须经 shell 调用；
// 统一自行加引号拼接，避免路径含空格时被 shell 拆分。
function runCorepack(args) {
  const env = {
    ...process.env,
    COREPACK_NPM_REGISTRY: NPM_REGISTRY,
    npm_config_registry: NPM_REGISTRY,
  };
  if (!isWindows) {
    return run("corepack", args, { env });
  }
  const command = ["corepack", ...args].map((part) => `"${part}"`).join(" ");
  const result = spawnSync(command, { stdio: "inherit", shell: true, env });
  return result.error == null && result.status === 0;
}

// 返回 "3.11" 形式的版本号；命令不存在或执行失败时返回 null。
function pythonVersion(command, versionArgs) {
  const result = spawnSync(
    command,
    [...versionArgs, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
    { encoding: "utf8" },
  );
  if (result.error || result.status !== 0) {
    return null;
  }
  return result.stdout.trim();
}

// 严格要求 Python 3.11：版本不符时宁可失败并给出指引，
// 也不要用其他版本静默建 venv（依赖是按 3.11 锁定的）。
function createVenvWithSystemPython(target) {
  const venvPath = join(target, "backend", ".venv");
  const candidates = isWindows
    ? [
        ["py", [`-${REQUIRED_PYTHON}`]],
        ["python", []],
      ]
    : [[`python${REQUIRED_PYTHON}`, []]];

  const found = [];
  for (const [command, versionArgs] of candidates) {
    const version = pythonVersion(command, versionArgs);
    if (version === REQUIRED_PYTHON) {
      return run(command, [...versionArgs, "-m", "venv", venvPath]);
    }
    if (version != null) {
      found.push(`${command} (${version})`);
    }
  }

  const detected = found.length > 0 ? `仅检测到 ${found.join("、")}` : "未检测到可用的 Python";
  process.stderr.write(
    `警告: 模板需要 Python ${REQUIRED_PYTHON}，${detected}。\n` +
      `请安装 Python ${REQUIRED_PYTHON}，或安装 uv（可自动下载 ${REQUIRED_PYTHON}）: pip install uv\n`,
  );
  return false;
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
      run("uv", ["venv", "--python", REQUIRED_PYTHON, "--seed", join(target, "backend", ".venv")]) &&
      run("uv", [
        "pip",
        "install",
        "--python",
        venvPython,
        "--index-url",
        PIP_INDEX_URL,
        "-r",
        requirements,
      ])
    );
  }
  if (!createVenvWithSystemPython(target)) {
    return false;
  }
  return run(venvPython, ["-m", "pip", "install", "--index-url", PIP_INDEX_URL, "-r", requirements]);
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
  process.stdout.write(`[1/2] 安装后端依赖 ...（PyPI 源: ${PIP_INDEX_URL}）\n`);
  if (!installBackend(target)) {
    return false;
  }
  process.stdout.write(`[2/2] 安装前端依赖 ...（npm 源: ${NPM_REGISTRY}）\n`);
  return installFrontend(target);
}

export function manualInstallSteps(target) {
  const pip = join("backend", ".venv", venvBinDir, "pip");
  return [
    "",
    `  cd ${target}`,
    "  uv venv --python 3.11 --seed backend/.venv   # 后端虚拟环境（或 python -m venv，需 3.11）",
    `  ${pip} install -i ${PIP_INDEX_URL} -r backend/requirements-dev.txt`,
    "  node scripts/init-frontend.mjs               # 前端依赖（corepack pnpm 按锁文件安装）",
    "",
  ].join("\n");
}
