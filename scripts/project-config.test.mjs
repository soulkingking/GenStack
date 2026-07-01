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
