#!/usr/bin/env node
// 固定使用锁文件安装前端依赖，避免不同开发环境解析出不同依赖版本。
import { join } from "node:path";
import process from "node:process";

import { repositoryRoot, runPnpm } from "./lib/run.mjs";

process.exit(
  runPnpm(["--dir", join(repositoryRoot, "frontend"), "install", "--frozen-lockfile"]),
);
