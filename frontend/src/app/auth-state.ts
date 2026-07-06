import { createContext, useContext } from "react";

export interface AuthState {
  /** 后端是否开启第三方登录；关闭时页面匿名访问，不请求用户信息。 */
  enabled: boolean;
}

// 默认按登录关闭处理：缺少 AuthGate 时页面保持匿名，不会发起用户信息请求。
export const AuthStateContext = createContext<AuthState>({ enabled: false });

export function useAuthState(): AuthState {
  return useContext(AuthStateContext);
}
