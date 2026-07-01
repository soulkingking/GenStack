# GenStack Template Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current uncommitted GenStack workspace with the quick-project-template structure while rebuilding its frontend with the existing React stack.

**Architecture:** Keep the existing Git identity and tracked design records, remove every untracked implementation file without backup, then build a minimal FastAPI application and a React SPA. Vite proxies `/api` during development; the production image builds the SPA and lets FastAPI serve it from the same origin.

**Tech Stack:** Python 3.11, FastAPI, pydantic-settings, React 19, Vite 8, TypeScript 6, pnpm, Tailwind CSS 4, shadcn/ui primitives, TanStack Query, React Router, Vitest, Testing Library, Docker Compose

---

## File map

- `backend/app/core/config.py`: environment-backed runtime settings.
- `backend/app/core/version.py`: reads the repository `VERSION` source of truth.
- `backend/app/api/health.py`: public health endpoint.
- `backend/app/main.py`: FastAPI construction, middleware, metadata endpoint, and static mounting.
- `backend/tests/test_api.py`: health and metadata contract tests.
- `frontend/src/api/system.ts`: typed health and metadata client.
- `frontend/src/app/app.tsx`: application routing and query provider.
- `frontend/src/pages/home-page.tsx`: minimal GenStack status page.
- `frontend/src/components/ui/{button,card}.tsx`: local shadcn/ui primitives.
- `frontend/src/index.css`: Tailwind theme and page styling.
- `frontend/vite.config.ts`: React plugin, version injection, aliases, fixed development port, and API proxy.
- `Dockerfile`: pnpm frontend build followed by Python runtime.
- `docker-compose.yml`: one application service with persistent `data/`.
- `scripts/*.sh`: fixed local start and packaging entry points.
- `README.md` and `docs/*.md`: truthful current capabilities and operating conventions.

### Task 1: Remove the old workspace and establish repository metadata

**Files:**
- Preserve: `.git/`
- Preserve: `LICENSE`
- Preserve: `docs/superpowers/specs/2026-07-01-genstack-template-rebuild-design.md`
- Preserve: `docs/superpowers/plans/2026-07-01-genstack-template-rebuild.md`
- Create: `.gitignore`
- Create: `.dockerignore`
- Create: `VERSION`
- Create: `CHANGELOG.md`
- Create: `data/.gitkeep`
- Create: `release-notes/README.md`

- [ ] **Step 1: Delete all untracked implementation without backup**

Run:

```bash
git clean -fdx
```

Expected: all untracked files listed before execution are removed; `.git/`, `LICENSE`, and the two tracked Superpowers documents remain.

- [ ] **Step 2: Add repository ignore rules**

Create `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/
*.egg-info/
.pytest_cache/

# Node
node_modules/
dist/
coverage/
*.local

# Data and secrets
data/*
!data/.gitkeep
.env
.env.local

# IDE and operating system
.idea/
.vscode/*
!.vscode/launch.json
!.vscode/tasks.json
!.vscode/extensions.json
.DS_Store
*.swp
```

Create `.dockerignore`:

```dockerignore
.git
.github
.idea
.vscode
.env
**/.venv
**/__pycache__
**/.pytest_cache
**/node_modules
**/dist
**/coverage
data/*
!data/.gitkeep
docs
release-notes
```

- [ ] **Step 3: Add version and release files**

Create `VERSION`:

```text
0.1.0
```

Create `CHANGELOG.md`:

```markdown
# Changelog

## 0.1.0

- Rebuilt GenStack from the quick-project-template structure.
- Replaced the template Vue frontend with React, Vite, TypeScript, and pnpm.
```

Create `release-notes/README.md`:

```markdown
# Release notes

Add one Markdown file per release, named after its Git tag, for example `v0.1.0.md`.
`VERSION`, the frontend package version, the changelog, and the tag must agree.
```

Create an empty `data/.gitkeep`.

- [ ] **Step 4: Verify the destructive boundary**

Run:

```bash
git status --short
find . -maxdepth 2 -type f | sort
```

Expected: no legacy `infra/`, root workspace package, Nacos configuration, Alembic migration, or old frontend source remains.

- [ ] **Step 5: Commit repository metadata**

```bash
git add .gitignore .dockerignore VERSION CHANGELOG.md data/.gitkeep release-notes/README.md
git commit -m "chore: reset GenStack template structure"
```

### Task 2: Build the minimal FastAPI backend contract

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/health.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/version.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_api.py`

- [ ] **Step 1: Add failing API contract tests**

Create `backend/tests/test_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_ok() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_meta_uses_genstack_identity() -> None:
    response = client.get("/api/meta")

    assert response.status_code == 200
    assert response.json() == {"name": "GenStack", "version": "0.1.0"}
```

- [ ] **Step 2: Add backend dependencies and verify the tests fail**

Create `backend/requirements.txt`:

```text
fastapi>=0.115.0,<1
uvicorn[standard]>=0.32.0,<1
pydantic-settings>=2.6.0,<3
python-multipart>=0.0.12,<1
```

Create `backend/requirements-dev.txt`:

```text
-r requirements.txt
httpx>=0.28.0,<1
pytest>=8.3.0,<10
```

Run:

```bash
python3.11 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements-dev.txt
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/test_api.py -q
```

Expected: FAIL because `app.main` does not exist.

- [ ] **Step 3: Implement configuration and version loading**

Create empty `backend/app/__init__.py`, `backend/app/api/__init__.py`, and
`backend/app/core/__init__.py`.

Create `backend/app/core/config.py`:

```python
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_SQLITE_URL = f"sqlite:///{(_REPOSITORY_ROOT / 'data' / 'app.db').as_posix()}"


class Settings(BaseSettings):
    """Runtime settings loaded from process environment and the repository .env."""

    model_config = SettingsConfigDict(
        env_file=str(_REPOSITORY_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = False
    database_url: str = _DEFAULT_SQLITE_URL
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        """Return normalized, non-empty browser origins for CORS middleware."""

        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings instance."""

    return Settings()
```

Create `backend/app/core/version.py`:

```python
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

APP_NAME = "GenStack"


def _read_version_file() -> str:
    try:
        raw_version = (_REPOSITORY_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return raw_version.splitlines()[0].strip() if raw_version else ""


# Source archives may omit VERSION, so development imports need an explicit fallback.
APP_VERSION = _read_version_file() or "0.0.0-dev"
```

- [ ] **Step 4: Implement the public endpoints and static mount**

Create `backend/app/api/health.py`:

```python
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Report that the API process can accept requests."""

    return {"status": "ok"}
```

Create `backend/app/main.py`:

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import health
from app.core.config import get_settings
from app.core.version import APP_NAME, APP_VERSION

settings = get_settings()

app = FastAPI(title=f"{APP_NAME} API", version=APP_VERSION, debug=settings.app_debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router, prefix="/api")


@app.get("/api/meta")
def meta() -> dict[str, str]:
    """Expose non-sensitive application identity to the frontend."""

    return {"name": APP_NAME, "version": APP_VERSION}


_repository_root = Path(__file__).resolve().parents[2]
_static_directory = _repository_root / "static"
# The frontend build only exists in the production image; local Vite development
# must leave FastAPI's own root unmounted.
if _static_directory.is_dir():
    app.mount("/", StaticFiles(directory=str(_static_directory), html=True), name="static")
```

- [ ] **Step 5: Run backend tests**

Run:

```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/test_api.py -q
```

Expected: `2 passed`.

- [ ] **Step 6: Commit the backend**

```bash
git add backend
git commit -m "feat: add minimal FastAPI backend"
```

### Task 3: Create the React and Vite foundation

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.app.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/components.json`
- Create: `frontend/src/vite-env.d.ts`
- Create: `frontend/src/test/setup.ts`

- [ ] **Step 1: Define the frontend package**

Create `frontend/package.json`:

```json
{
  "name": "@genstack/frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "packageManager": "pnpm@10.33.2",
  "engines": {
    "node": ">=22.12.0"
  },
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "oxlint src --deny-warnings",
    "typecheck": "tsc -b --pretty false",
    "test": "vitest run",
    "check": "pnpm lint && pnpm typecheck && pnpm test && pnpm build"
  },
  "dependencies": {
    "@radix-ui/react-slot": "^1.3.0",
    "@tanstack/react-query": "^5.101.2",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "lucide-react": "^1.22.0",
    "react": "^19.2.7",
    "react-dom": "^19.2.7",
    "react-router": "^7.9.4",
    "tailwind-merge": "^3.6.0"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.3.2",
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@types/node": "^26.0.1",
    "@types/react": "^19.2.17",
    "@types/react-dom": "^19.2.3",
    "@vitejs/plugin-react": "^6.0.3",
    "jsdom": "^29.1.1",
    "oxlint": "^1.72.0",
    "tailwindcss": "^4.3.2",
    "typescript": "~6.0.3",
    "vite": "^8.1.0",
    "vitest": "^4.1.9"
  }
}
```

- [ ] **Step 2: Add TypeScript project references**

Create `frontend/tsconfig.json`:

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

Create `frontend/tsconfig.app.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "types": ["vite/client", "vitest/globals"],
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```

Create `frontend/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "noEmit": true,
    "types": ["node"]
  },
  "include": ["vite.config.ts", "vitest.config.ts"]
}
```

- [ ] **Step 3: Configure Vite 8 and Vitest**

Create `frontend/vite.config.ts`:

```typescript
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const currentDirectory = dirname(fileURLToPath(import.meta.url));
const version =
  readFileSync(join(currentDirectory, "..", "VERSION"), "utf8").trim().split("\n")[0]?.trim() ||
  "0.0.0-dev";

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(version),
  },
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": join(currentDirectory, "src"),
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
```

Create `frontend/vitest.config.ts`:

```typescript
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const currentDirectory = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": join(currentDirectory, "src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
```

Create `frontend/src/test/setup.ts`:

```typescript
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 4: Add browser and shadcn metadata**

Create `frontend/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="GenStack full-stack application template" />
    <title>GenStack</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `frontend/components.json`:

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "css": "src/index.css",
    "baseColor": "neutral",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide"
}
```

Create `frontend/src/vite-env.d.ts`:

```typescript
/// <reference types="vite/client" />

declare const __APP_VERSION__: string;
```

- [ ] **Step 5: Install and lock dependencies**

Run:

```bash
corepack pnpm --dir frontend install
```

Expected: `frontend/pnpm-lock.yaml` is created with no npm lockfile.

- [ ] **Step 6: Commit the frontend foundation**

```bash
git add frontend
git commit -m "chore: create React Vite frontend"
```

### Task 4: Implement the status page with tests

**Files:**
- Create: `frontend/src/api/system.ts`
- Create: `frontend/src/api/system.test.ts`
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/src/components/ui/button.tsx`
- Create: `frontend/src/components/ui/card.tsx`
- Create: `frontend/src/pages/home-page.tsx`
- Create: `frontend/src/pages/home-page.test.tsx`
- Create: `frontend/src/app/app.tsx`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/index.css`

- [ ] **Step 1: Write failing API client tests**

Create `frontend/src/api/system.test.ts`:

```typescript
import { getHealth, getMeta } from "@/api/system";

describe("system API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads health", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response('{"status":"ok"}')));
    await expect(getHealth()).resolves.toEqual({ status: "ok" });
  });

  it("rejects unsuccessful responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 503 })));
    await expect(getMeta()).rejects.toThrow("Request failed with status 503");
  });
});
```

Run:

```bash
corepack pnpm --dir frontend test
```

Expected: FAIL because `@/api/system` does not exist.

- [ ] **Step 2: Implement the system API client**

Create `frontend/src/api/system.ts`:

```typescript
export interface Health {
  status: "ok";
}

export interface ApplicationMeta {
  name: string;
  version: string;
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export function getHealth(): Promise<Health> {
  return request<Health>("/api/health");
}

export function getMeta(): Promise<ApplicationMeta> {
  return request<ApplicationMeta>("/api/meta");
}
```

Run:

```bash
corepack pnpm --dir frontend test
```

Expected: API tests pass.

- [ ] **Step 3: Write the failing home page test**

Create `frontend/src/pages/home-page.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";

import { HomePage } from "@/pages/home-page";

vi.mock("@/api/system", () => ({
  getHealth: vi.fn().mockResolvedValue({ status: "ok" }),
  getMeta: vi.fn().mockResolvedValue({ name: "GenStack", version: "0.1.0" }),
}));

it("shows application identity and healthy API status", async () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <HomePage />
    </QueryClientProvider>,
  );

  expect(await screen.findByRole("heading", { name: "GenStack" })).toBeInTheDocument();
  expect(await screen.findByText("API 正常")).toBeInTheDocument();
  expect(screen.getByText(/0\.1\.0/)).toBeInTheDocument();
});
```

Run:

```bash
corepack pnpm --dir frontend test
```

Expected: FAIL because `HomePage` does not exist.

- [ ] **Step 4: Add UI utilities and local shadcn primitives**

Create `frontend/src/lib/utils.ts`:

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
```

Create `frontend/src/components/ui/button.tsx`:

```tsx
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90",
        outline: "border border-border bg-background px-4 py-2 hover:bg-muted",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export function Button({ asChild = false, className, variant, ...props }: ButtonProps) {
  const Component = asChild ? Slot : "button";
  return <Component className={cn(buttonVariants({ variant }), className)} {...props} />;
}
```

Create `frontend/src/components/ui/card.tsx`:

```tsx
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-xl border bg-card text-card-foreground", className)} {...props} />;
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-1.5 p-6", className)} {...props} />;
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn("font-semibold leading-none tracking-tight", className)} {...props} />;
}

export function CardDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm text-muted-foreground", className)} {...props} />;
}

export function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-6 pt-0", className)} {...props} />;
}
```

- [ ] **Step 5: Implement the home page and application entry**

Create `frontend/src/pages/home-page.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";
import { Activity, RotateCw } from "lucide-react";

import { getHealth, getMeta } from "@/api/system";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function HomePage() {
  const health = useQuery({ queryKey: ["system", "health"], queryFn: getHealth });
  const meta = useQuery({ queryKey: ["system", "meta"], queryFn: getMeta });
  const isAvailable = health.data?.status === "ok" && meta.isSuccess;

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl items-center px-6 py-12">
      <section className="w-full space-y-8">
        <div className="space-y-3">
          <p className="text-sm font-medium uppercase tracking-[0.24em] text-muted-foreground">
            Full-stack foundation
          </p>
          <h1 className="text-5xl font-semibold tracking-tight">{meta.data?.name ?? "GenStack"}</h1>
          <p className="max-w-2xl text-lg text-muted-foreground">
            一个最小、可部署并可继续演进的 React 与 FastAPI 项目模板。
          </p>
        </div>

        <Card className="max-w-xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="size-5" aria-hidden="true" />
              服务状态
            </CardTitle>
            <CardDescription>前端通过同源 /api 接口检查后端。</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center justify-between gap-4">
            <div>
              <p className={isAvailable ? "font-medium text-emerald-700" : "font-medium text-amber-700"}>
                {health.isPending || meta.isPending ? "正在检查" : isAvailable ? "API 正常" : "API 不可用"}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                版本 {meta.data?.version ?? __APP_VERSION__}
              </p>
            </div>
            <Button
              variant="outline"
              onClick={() => {
                void Promise.all([health.refetch(), meta.refetch()]);
              }}
            >
              <RotateCw className="mr-2 size-4" aria-hidden="true" />
              重新检查
            </Button>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
```

Create `frontend/src/app/app.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router";

import { HomePage } from "@/pages/home-page";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="*" element={<HomePage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

Create `frontend/src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/app/app";
import "@/index.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Missing #root application mount point");
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

Create `frontend/src/index.css`:

```css
@import "tailwindcss";

:root {
  color: #171717;
  background: #f7f6f2;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-synthesis: none;
  text-rendering: optimizeLegibility;

  --background: #f7f6f2;
  --foreground: #171717;
  --card: #ffffff;
  --card-foreground: #171717;
  --primary: #171717;
  --primary-foreground: #fafafa;
  --muted: #eceae4;
  --muted-foreground: #6b6963;
  --border: #dedbd3;
  --ring: #8b8880;
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-border: var(--border);
  --color-ring: var(--ring);
}

* {
  border-color: var(--border);
}

body {
  margin: 0;
  min-width: 320px;
  min-height: 100vh;
  background:
    radial-gradient(circle at top right, rgb(212 227 220 / 55%), transparent 32rem),
    var(--background);
}

button {
  font: inherit;
}
```

- [ ] **Step 6: Run frontend checks**

Run:

```bash
corepack pnpm --dir frontend check
```

Expected: lint, typecheck, two test files, and production build pass.

- [ ] **Step 7: Commit the frontend**

```bash
git add frontend
git commit -m "feat: add GenStack status frontend"
```

### Task 5: Add local scripts and single-image deployment

**Files:**
- Create: `.env.example`
- Create: `scripts/init-frontend.sh`
- Create: `scripts/start-backend.sh`
- Create: `scripts/start-frontend.sh`
- Create: `scripts/package.sh`
- Create: `Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Add environment contract**

Create `.env.example`:

```dotenv
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=false

# Reserved for the first persistence-backed feature. The current API does not open a database.
# DATABASE_URL=sqlite:////absolute/path/to/data/app.db

CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

- [ ] **Step 2: Add fixed development scripts**

Create `scripts/init-frontend.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec corepack pnpm --dir "${ROOT}/frontend" install --frozen-lockfile
```

Create `scripts/start-backend.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${ROOT}/backend"
UVICORN=(uvicorn)
if [[ -x "${ROOT}/backend/.venv/bin/uvicorn" ]]; then
  UVICORN=("${ROOT}/backend/.venv/bin/uvicorn")
fi
cd "${ROOT}/backend"
exec "${UVICORN[@]}" app.main:app --reload --host 127.0.0.1 --port 8000
```

Create `scripts/start-frontend.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec corepack pnpm --dir "${ROOT}/frontend" dev
```

Create `scripts/package.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
corepack pnpm --dir "${ROOT}/frontend" install --frozen-lockfile
corepack pnpm --dir "${ROOT}/frontend" build
docker build -f "${ROOT}/Dockerfile" -t genstack:latest "${ROOT}"
```

Run:

```bash
chmod +x scripts/*.sh
bash -n scripts/*.sh
```

Expected: shell syntax validation passes.

- [ ] **Step 3: Add the multi-stage image**

Create `Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS frontend-build
WORKDIR /build/frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN corepack pnpm install --frozen-lockfile
COPY frontend/ ./
COPY VERSION /build/VERSION
RUN corepack pnpm build

FROM python:3.11-slim-bookworm AS runtime
WORKDIR /app

ARG TZ=Asia/Shanghai
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend \
    TZ=${TZ}

COPY VERSION /app/VERSION
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/app/ /app/backend/app/
COPY --from=frontend-build /build/frontend/dist /app/static/

RUN mkdir -p /app/data
VOLUME ["/app/data"]
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Add Compose**

Create `docker-compose.yml`:

```yaml
name: genstack

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    image: genstack:latest
    ports:
      - "8000:8000"
    environment:
      APP_HOST: "0.0.0.0"
      APP_PORT: "8000"
      APP_DEBUG: "false"
      CORS_ORIGINS: "http://localhost:8000"
    volumes:
      - ./data:/app/data
    healthcheck:
      test:
        [
          "CMD",
          "python",
          "-c",
          "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)",
        ]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 5s
    restart: unless-stopped
```

- [ ] **Step 5: Validate deployment configuration**

Run:

```bash
docker compose config --quiet
docker build -t genstack:latest .
```

Expected: Compose validation and the multi-stage image build succeed.

- [ ] **Step 6: Commit deployment files**

```bash
git add .env.example scripts Dockerfile docker-compose.yml
git commit -m "build: add single-image deployment"
```

### Task 6: Replace template documentation with truthful GenStack documentation

**Files:**
- Create: `README.md`
- Create: `backend/README.md`
- Create: `frontend/README.md`
- Create: `docs/架构标准.md`
- Create: `docs/前端框架标准.md`
- Create: `docs/调试标准.md`
- Create: `docs/版本标准.md`

- [ ] **Step 1: Write the root README**

Create `README.md` with these exact sections and facts:

```markdown
# GenStack

GenStack 是一个采用 React 与 FastAPI 的最小全栈项目模板。它沿用
quick-project-template 的单仓库、固定端口、单镜像和 `data/` 持久化约定，
但前端使用 React 技术栈。

## 当前能力

- `GET /api/health`：API 存活检查
- `GET /api/meta`：应用名称和版本
- React 状态首页
- Vite 开发代理
- FastAPI 同源静态资源托管
- Docker Compose 单容器交付

当前不包含认证、用户管理、API Key、ORM、数据库迁移或 Nacos。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 | Python 3.11、FastAPI、pydantic-settings |
| 前端 | React 19、Vite 8、TypeScript 6、pnpm、Tailwind CSS、shadcn/ui、TanStack Query |
| 数据 | 预留 `DATABASE_URL`，默认持久化目录为 `data/` |
| 交付 | 多阶段 Dockerfile、Docker Compose |

## 本地开发

```bash
cp .env.example .env
python3.11 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements-dev.txt
bash scripts/init-frontend.sh
```

分别启动两个进程：

```bash
bash scripts/start-backend.sh
bash scripts/start-frontend.sh
```

访问 <http://127.0.0.1:5173>。后端固定使用
<http://127.0.0.1:8000>，Vite 将 `/api` 代理到该端口。

## 验证

```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -q
corepack pnpm --dir frontend check
docker compose config --quiet
```

## Docker

```bash
bash scripts/package.sh
docker compose up -d
```

访问 <http://127.0.0.1:8000>。容器内由 FastAPI 同时提供静态页面和 API。

## 文档

- [架构标准](docs/架构标准.md)
- [前端框架标准](docs/前端框架标准.md)
- [调试标准](docs/调试标准.md)
- [版本标准](docs/版本标准.md)
```

- [ ] **Step 2: Document backend and frontend boundaries**

Create `backend/README.md`:

```markdown
# GenStack backend

后端是最小 FastAPI 应用，只提供 `/api/health`、`/api/meta` 和生产静态资源托管。
配置由 `app/core/config.py` 从环境变量及仓库根 `.env` 读取。

本地测试：

```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -q
```
```

Create `frontend/README.md`:

```markdown
# GenStack frontend

前端采用 React 19、Vite 8、TypeScript 6、pnpm、Tailwind CSS、shadcn/ui 和
TanStack Query。开发服务器固定为 `127.0.0.1:5173`，并将 `/api` 代理到
`127.0.0.1:8000`。

```bash
corepack pnpm install
corepack pnpm check
```
```

- [ ] **Step 3: Add concise operating standards**

Create `docs/架构标准.md`:

```markdown
# 架构标准

## 应用边界

`frontend/` 与 `backend/` 是独立应用。开发时分别运行，浏览器只请求相对路径
`/api`；Vite 将请求代理到 FastAPI。生产镜像把前端构建结果复制到 `/app/static`，
由 FastAPI 同源提供页面和 API。

## API

所有后端接口使用 `/api` 前缀。当前公开接口只有：

- `GET /api/health`
- `GET /api/meta`

新增业务时保持路由、业务逻辑和持久化职责分离，禁止把复杂业务直接写进
`app/main.py`。

## 配置与数据

配置由 `backend/app/core/config.py` 统一读取。密钥不得写入仓库。运行时数据必须
写入 `data/`，容器部署必须挂载该目录。`DATABASE_URL` 只是未来持久化功能的配置
入口；当前应用不会连接数据库。

## 当前非目标

当前没有认证、用户、API Key、ORM、数据库迁移、Nacos 或服务发现。引入这些能力
前必须先定义真实接口和运行约束，并同步更新本文档。
```

Create `docs/前端框架标准.md`:

```markdown
# 前端框架标准

- 使用 React 函数组件和 TypeScript 严格模式。
- 服务端状态统一由 TanStack Query 管理，不复制到组件级共享状态。
- 通用 UI 使用 `src/components/ui/` 中的本地 shadcn/ui primitive。
- 源码通过 `@/` 指向 `src/`；API 调用收敛到 `src/api/`。
- 开发服务器固定为 `127.0.0.1:5173`，`/api` 固定代理到
  `127.0.0.1:8000`。
- 依赖只使用 pnpm 管理，不提交 npm 或 Yarn lockfile。
- 合并前运行 `corepack pnpm --dir frontend check`，必须通过 lint、类型检查、
  单元测试和生产构建。
```

Create `docs/调试标准.md`:

```markdown
# 调试标准

后端固定使用 `127.0.0.1:8000`，前端固定使用 `127.0.0.1:5173`。端口被占用时
应查找并结束旧进程，不通过更换端口规避。

排查前后端联调问题时按以下顺序执行：

1. 请求 `http://127.0.0.1:8000/api/health`；
2. 检查 `.env` 与后端启动日志；
3. 检查 Vite `/api` 代理；
4. 检查浏览器请求和前端状态。

验证命令：

```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -q
corepack pnpm --dir frontend check
docker compose config --quiet
```
```

Create `docs/版本标准.md`:

```markdown
# 版本标准

仓库根目录 `VERSION` 是应用版本唯一真源，使用语义化版本。发版前必须：

1. 更新 `VERSION`；
2. 同步 `frontend/package.json` 的 `version`；
3. 更新 `CHANGELOG.md` 和对应的 `release-notes/vX.Y.Z.md`；
4. 通过全部验证；
5. 创建与版本一致的 Git 标签，例如 `v0.1.0`。

后端 `/api/meta` 与前端构建常量都从 `VERSION` 读取，不维护第二份运行时版本。
```

- [ ] **Step 4: Audit documentation for stale template claims**

Run:

```bash
rg -n "Vue|npm |package-lock|ai-webapp-template|AUTH_USERNAME|AUTH_PASSWORD|admin/admin|Nacos|Alembic" \
  README.md backend frontend docs scripts Dockerfile docker-compose.yml .env.example
```

Expected: no stale claim remains. Mentions that explicitly state an absent capability are
allowed only in the root README or architecture documentation.

- [ ] **Step 5: Commit documentation**

```bash
git add README.md backend/README.md frontend/README.md docs
git commit -m "docs: document rebuilt GenStack template"
```

### Task 7: Final verification and comment audit

**Files:**
- Inspect: all changed files
- Modify: only files failing the checks or containing stale comments/documentation

- [ ] **Step 1: Run backend verification**

```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -q
PYTHONPATH=backend backend/.venv/bin/python -c "from app.main import app; assert app.title == 'GenStack API'"
```

Expected: two tests pass and the import assertion exits successfully.

- [ ] **Step 2: Run frontend verification**

```bash
corepack pnpm --dir frontend check
```

Expected: Oxlint, TypeScript, Vitest, and Vite build all pass.

- [ ] **Step 3: Run the API and verify live contracts**

Run `bash scripts/start-backend.sh`, then:

```bash
curl --fail --silent http://127.0.0.1:8000/api/health
curl --fail --silent http://127.0.0.1:8000/api/meta
```

Expected:

```json
{"status":"ok"}
{"name":"GenStack","version":"0.1.0"}
```

- [ ] **Step 4: Verify the production image**

```bash
docker compose up -d --build
curl --fail --silent http://127.0.0.1:8000/ | rg "<title>GenStack</title>"
curl --fail --silent http://127.0.0.1:8000/api/health
docker compose down
```

Expected: the page and API both respond from port `8000`.

- [ ] **Step 5: Audit comments, docs, and diff**

```bash
git diff origin/main --check
rg -n "TODO|TBD|ai-webapp-template|package-lock|@vitejs/plugin-vue|shadcn-vue" \
  --glob '!docs/superpowers/**' .
git status --short
```

Expected: no whitespace errors, placeholders, stale implementation comments, Vue files, or
npm lockfiles. Every non-obvious compatibility or deployment branch has a concise reason
comment, and documentation matches the actual endpoints and commands.

- [ ] **Step 6: Commit final corrections if needed**

```bash
git add -A
git commit -m "chore: finalize GenStack template rebuild"
```

Expected: skip this commit when the working tree is already clean.
