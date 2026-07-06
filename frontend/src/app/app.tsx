import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { BrowserRouter, Route, Routes } from "react-router";

import { AuthGate } from "@/app/auth-gate";
import { HomePage } from "@/pages/home-page";

// 短时间复用系统状态，避免组件重新挂载时立即重复请求；瞬时失败只重试一次。
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthGate>
        <BrowserRouter>
          <Routes>
            <Route path="*" element={<HomePage />} />
          </Routes>
        </BrowserRouter>
      </AuthGate>
      {/* 仅开发构建包含调试面板，生产构建经死代码消除后不含任何字节。 */}
      {import.meta.env.DEV ? <ReactQueryDevtools initialIsOpen={false} /> : null}
    </QueryClientProvider>
  );
}
