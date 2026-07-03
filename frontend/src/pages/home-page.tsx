import { useQuery } from "@tanstack/react-query";
import { Activity, RotateCw } from "lucide-react";

import { getHealth, getMeta } from "@/api/system";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function HomePage() {
  const health = useQuery({ queryKey: ["system", "health"], queryFn: getHealth });
  const meta = useQuery({ queryKey: ["system", "meta"], queryFn: getMeta });
  const isAvailable = health.data?.status === "ok" && meta.isSuccess;
  // 首次加载与手动刷新共用同一进行中状态，期间禁用按钮防止重复触发。
  const isChecking = health.isFetching || meta.isFetching;

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
              {/* role="status" 隐含 aria-live=polite，状态变化时读屏器自动播报。 */}
              <p
                role="status"
                className={
                  isAvailable
                    ? "font-medium text-emerald-700 dark:text-emerald-400"
                    : "font-medium text-amber-700 dark:text-amber-400"
                }
              >
                {health.isPending || meta.isPending
                  ? "正在检查"
                  : isAvailable
                    ? "API 正常"
                    : "API 不可用"}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                版本 {meta.data?.version ?? __APP_VERSION__}
              </p>
            </div>
            <Button
              variant="outline"
              disabled={isChecking}
              onClick={() => {
                // 两个接口互不依赖，并行刷新可避免串行等待，同时不阻塞点击事件。
                void Promise.all([health.refetch(), meta.refetch()]);
              }}
            >
              <RotateCw
                className={cn("mr-2 size-4", isChecking && "animate-spin")}
                aria-hidden="true"
              />
              重新检查
            </Button>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
