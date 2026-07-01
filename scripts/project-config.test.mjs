import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repositoryRoot = join(dirname(fileURLToPath(import.meta.url)), "..");

async function readRepositoryFile(path) {
  return readFile(join(repositoryRoot, path), "utf8");
}

test("Docker build defaults to domestic mirrors and installs the runtime timezone", async () => {
  const dockerfile = await readRepositoryFile("Dockerfile");
  const packageScript = await readRepositoryFile("scripts/package.sh");

  for (const requiredFragment of [
    "ARG NODE_IMAGE=docker.m.daocloud.io/library/node:22-bookworm-slim",
    "ARG PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.11-slim-bookworm",
    "ARG NPM_REGISTRY=https://registry.npmmirror.com",
    "ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/",
    "ARG DEBIAN_MIRROR=mirrors.tuna.tsinghua.edu.cn",
    "ARG TZ=Asia/Shanghai",
    "DEBIAN_FRONTEND=noninteractive",
    "ca-certificates",
    "tzdata",
    "/usr/share/zoneinfo/${TZ}",
    "/etc/timezone",
  ]) {
    assert.ok(dockerfile.includes(requiredFragment), requiredFragment);
  }

  for (const buildArgument of [
    "NODE_IMAGE",
    "PYTHON_IMAGE",
    "NPM_REGISTRY",
    "PIP_INDEX_URL",
    "DEBIAN_MIRROR",
    "TZ",
  ]) {
    const expectedArgument = `--build-arg "${buildArgument}=\${${buildArgument}}"`;
    assert.ok(packageScript.includes(expectedArgument), expectedArgument);
  }
});

test("VS Code exposes backend, frontend, browser, and full-stack launches", async () => {
  const extensions = JSON.parse(await readRepositoryFile(".vscode/extensions.json"));
  const settings = JSON.parse(await readRepositoryFile(".vscode/settings.json"));
  const tasks = JSON.parse(await readRepositoryFile(".vscode/tasks.json"));
  const launch = JSON.parse(await readRepositoryFile(".vscode/launch.json"));

  assert.deepEqual(
    new Set(extensions.recommendations),
    new Set([
      "ms-python.python",
      "ms-python.debugpy",
      "bradlc.vscode-tailwindcss",
      "oxc.oxc-vscode",
      "ms-azuretools.vscode-docker",
    ]),
  );
  assert.equal(
    settings["python.defaultInterpreterPath"],
    "${workspaceFolder}/backend/.venv/bin/python",
  );
  assert.equal(settings["python.testing.pytestEnabled"], true);
  assert.equal(settings["python.testing.cwd"], "${workspaceFolder}/backend");
  assert.deepEqual(settings["python.testing.pytestArgs"], ["tests"]);

  assert.deepEqual(
    tasks.tasks.map(({ label }) => label),
    ["debug: kill backend port 8000", "debug: kill frontend port 5173"],
  );
  assert.deepEqual(
    launch.configurations.map(({ name }) => name),
    [
      "Python: FastAPI (后端)",
      "Python: FastAPI (后端, 热重载)",
      "pnpm: 前端开发 (Vite)",
      "Chrome: 前端页面",
    ],
  );
  assert.deepEqual(launch.compounds[0].configurations, [
    "Python: FastAPI (后端)",
    "pnpm: 前端开发 (Vite)",
  ]);
  assert.equal(launch.compounds[0].stopAll, true);
});
