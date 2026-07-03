#!/usr/bin/env node
// 构建前端并打包 Docker 镜像。默认使用 DaoCloud 基础镜像与国内源，
// 可通过同名环境变量切换到官方源（与 Dockerfile 默认值保持一致）。
import { join } from "node:path";
import process from "node:process";

import { repositoryRoot, run, runPnpm } from "./lib/run.mjs";

const buildArgs = {
  NODE_IMAGE: process.env.NODE_IMAGE ?? "docker.m.daocloud.io/library/node:22-bookworm-slim",
  PYTHON_IMAGE:
    process.env.PYTHON_IMAGE ?? "docker.m.daocloud.io/library/python:3.11-slim-bookworm",
  NPM_REGISTRY: process.env.NPM_REGISTRY ?? "https://registry.npmmirror.com",
  PIP_INDEX_URL: process.env.PIP_INDEX_URL ?? "https://mirrors.aliyun.com/pypi/simple/",
  DEBIAN_MIRROR: process.env.DEBIAN_MIRROR ?? "mirrors.tuna.tsinghua.edu.cn",
  TZ: process.env.TZ ?? "Asia/Shanghai",
};

const frontend = join(repositoryRoot, "frontend");
if (runPnpm(["--dir", frontend, "install", "--frozen-lockfile"]) !== 0) {
  process.exit(1);
}
if (runPnpm(["--dir", frontend, "build"]) !== 0) {
  process.exit(1);
}

process.exit(
  run("docker", [
    "build",
    ...Object.entries(buildArgs).flatMap(([key, value]) => ["--build-arg", `${key}=${value}`]),
    "-f",
    join(repositoryRoot, "Dockerfile"),
    "-t",
    "genstack:latest",
    repositoryRoot,
  ]),
);
