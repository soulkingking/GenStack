# GenStack frontend

前端采用 React 19、Vite 8、TypeScript 6、pnpm、Tailwind CSS、shadcn/ui 和
TanStack Query。开发服务器固定为 `127.0.0.1:5173`，并将 `/api` 代理到
`127.0.0.1:8000`。

`AuthGate` 在渲染页面前检查 `/api/auth/session`。OAuth2 回调含有 `code/state`
时，前端只把它们提交给同源 FastAPI；客户端密钥和 Access Token 都不会进入前端
状态或存储。首次兑换失败会重新授权一次，连续失败则停止跳转并显示重试入口。

从仓库根目录运行：

```bash
corepack pnpm --dir frontend install
corepack pnpm --dir frontend check
```
