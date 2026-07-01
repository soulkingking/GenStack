export interface Health {
  status: "ok";
}

export interface ApplicationMeta {
  name: string;
  version: string;
}

// 系统接口共享相同的 JSON 与错误契约，避免页面层重复处理 HTTP 状态。
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
