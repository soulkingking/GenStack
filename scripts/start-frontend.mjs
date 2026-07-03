#!/usr/bin/env node
// 启动 Vite 开发服务器（127.0.0.1:5173，/api 代理到后端 8000）。
import { join } from "node:path";
import process from "node:process";

import { repositoryRoot, runPnpm } from "./lib/run.mjs";

process.exit(runPnpm(["--dir", join(repositoryRoot, "frontend"), "dev"]));
