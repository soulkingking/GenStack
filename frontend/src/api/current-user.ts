export interface CurrentUser {
  user_id: number | null;
  username: string | null;
  real_name: string | null;
  dept_id: number | null;
  dept_name: string | null;
  company_id: number | null;
  roles: string[];
  permissions: string[];
  menu_permissions: string[];
  role_permissions: string[];
}

// 后端只返回白名单字段；浏览器永远拿不到 Access Token 本身。
export async function getCurrentUser(): Promise<CurrentUser> {
  const response = await fetch("/api/current-user", {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return (await response.json()) as CurrentUser;
}
