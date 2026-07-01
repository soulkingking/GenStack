import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router";

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
      <BrowserRouter>
        <Routes>
          <Route path="*" element={<HomePage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
