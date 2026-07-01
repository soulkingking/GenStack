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
