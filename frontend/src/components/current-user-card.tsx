import { useQuery } from "@tanstack/react-query";
import { User } from "lucide-react";

import { getCurrentUser } from "@/api/current-user";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface UserFieldProps {
  label: string;
  value: string;
}

function UserField({ label, value }: UserFieldProps) {
  return (
    <div>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}

export function CurrentUserCard() {
  const user = useQuery({ queryKey: ["current-user"], queryFn: getCurrentUser });

  return (
    <Card className="max-w-xl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <User className="size-5" aria-hidden="true" />
          当前用户
        </CardTitle>
        <CardDescription>由后端代理第三方用户信息接口，仅展示白名单字段。</CardDescription>
      </CardHeader>
      <CardContent>
        {user.isPending ? (
          <p role="status" className="text-sm text-muted-foreground">
            正在加载用户信息
          </p>
        ) : user.isError ? (
          <p role="alert" className="text-sm font-medium text-amber-700 dark:text-amber-400">
            用户信息暂时不可用，请稍后重试。
          </p>
        ) : (
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <UserField
              label="姓名"
              value={user.data.real_name ?? user.data.username ?? "未知用户"}
            />
            <UserField label="账号" value={user.data.username ?? "—"} />
            <UserField label="部门" value={user.data.dept_name ?? "—"} />
            <UserField
              label="角色"
              value={user.data.roles.length > 0 ? user.data.roles.join("、") : "—"}
            />
          </dl>
        )}
      </CardContent>
    </Card>
  );
}
