# GenStack frontend

前端采用 React 19、Vite 8、TypeScript 6、pnpm、Tailwind CSS、shadcn/ui 和
TanStack Query。开发服务器固定为 `127.0.0.1:5173`，并将 `/api` 代理到
`127.0.0.1:8000`。

从仓库根目录运行：

```bash
corepack pnpm --dir frontend install
corepack pnpm --dir frontend check
```
