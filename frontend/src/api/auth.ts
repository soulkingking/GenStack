export interface SessionStatus {
  /** 后端是否开启第三方登录；关闭时页面匿名访问。 */
  enabled: boolean;
  authenticated: boolean;
}

export const LOGIN_URL = "/api/auth/login";

function isSessionStatus(value: unknown): value is SessionStatus {
  return (
    typeof value === "object" &&
    value !== null &&
    "enabled" in value &&
    typeof value.enabled === "boolean" &&
    "authenticated" in value &&
    typeof value.authenticated === "boolean"
  );
}

async function requestSessionStatus(path: string, init?: RequestInit): Promise<SessionStatus> {
  const response = await fetch(path, {
    ...init,
    credentials: "same-origin",
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      Accept: "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`Authentication request failed with status ${response.status}`);
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new Error("Invalid authentication response");
  }
  // 认证边界只接受布尔会话状态，避免前端意外开始依赖后端 Token 数据。
  if (!isSessionStatus(body)) {
    throw new Error("Invalid authentication response");
  }
  return body;
}

export function getSession(): Promise<SessionStatus> {
  return requestSessionStatus("/api/auth/session");
}

export function exchangeAuthorizationCode(
  code: string,
  state: string,
): Promise<SessionStatus> {
  return requestSessionStatus("/api/auth/token", {
    method: "POST",
    body: JSON.stringify({ code, state }),
  });
}
