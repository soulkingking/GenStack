#!/usr/bin/env node
// 启动 FastAPI 开发服务器（127.0.0.1:8000，热重载）。
import { existsSync } from "node:fs";
import { join } from "node:path";
import process from "node:process";

import { isWindows, repositoryRoot, run } from "./lib/run.mjs";

const backend = join(repositoryRoot, "backend");
const venvUvicorn = join(
  backend,
  ".venv",
  isWindows ? "Scripts" : "bin",
  isWindows ? "uvicorn.exe" : "uvicorn",
);
// 优先使用项目虚拟环境，未初始化时才回退到 PATH 中的 uvicorn。
const uvicorn = existsSync(venvUvicorn) ? venvUvicorn : "uvicorn";

process.exit(
  run(uvicorn, ["app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"], {
    cwd: backend,
    env: { ...process.env, PYTHONPATH: backend },
  }),
);
