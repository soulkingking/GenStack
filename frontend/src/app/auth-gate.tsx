import { useEffect, useState, type ReactNode } from "react";

import {
  exchangeAuthorizationCode,
  getSession,
  LOGIN_URL,
} from "@/api/auth";
import { Button } from "@/components/ui/button";

const OAUTH_RETRY_KEY = "genstack_oauth_retry";
const CALLBACK_PARAMETERS = ["code", "state", "error", "error_description"];

type AuthPhase = "checking" | "exchanging" | "redirecting" | "authenticated" | "error";

interface AuthGateProps {
  children: ReactNode;
  redirect?: (url: string) => void;
  replaceUrl?: (url: string) => void;
}

function redirectBrowser(url: string) {
  window.location.assign(url);
}

function replaceBrowserUrl(url: string) {
  window.history.replaceState({}, document.title, url);
}

function callbackFreeUrl(): string {
  const url = new URL(window.location.href);
  for (const parameter of CALLBACK_PARAMETERS) {
    url.searchParams.delete(parameter);
  }
  return `${url.pathname}${url.search}${url.hash}`;
}

export function AuthGate({
  children,
  redirect = redirectBrowser,
  replaceUrl = replaceBrowserUrl,
}: AuthGateProps) {
  const [phase, setPhase] = useState<AuthPhase>("checking");

  useEffect(() => {
    let cancelled = false;

    const restartAuthorizationOrShowError = () => {
      if (window.sessionStorage.getItem(OAUTH_RETRY_KEY) === "1") {
        setPhase("error");
        return;
      }

      // 单标签页最多自动重试一次，避免密钥或回调配置错误时形成重定向循环。
      window.sessionStorage.setItem(OAUTH_RETRY_KEY, "1");
      setPhase("redirecting");
      redirect(LOGIN_URL);
    };

    const authenticate = async () => {
      try {
        const session = await getSession();
        if (cancelled) return;

        if (session.authenticated) {
          window.sessionStorage.removeItem(OAUTH_RETRY_KEY);
          setPhase("authenticated");
          return;
        }

        const query = new URLSearchParams(window.location.search);
        const code = query.get("code");
        const state = query.get("state");
        if (query.has("error") || !code || !state) {
          if (!code && !query.has("error")) {
            setPhase("redirecting");
            redirect(LOGIN_URL);
            return;
          }
          restartAuthorizationOrShowError();
          return;
        }

        setPhase("exchanging");
        const exchanged = await exchangeAuthorizationCode(code, state);
        if (cancelled) return;
        if (!exchanged.authenticated) {
          restartAuthorizationOrShowError();
          return;
        }

        window.sessionStorage.removeItem(OAUTH_RETRY_KEY);
        replaceUrl(callbackFreeUrl());
        setPhase("authenticated");
      } catch {
        if (!cancelled) {
          restartAuthorizationOrShowError();
        }
      }
    };

    void authenticate();
    return () => {
      cancelled = true;
    };
  }, [redirect, replaceUrl]);

  if (phase === "authenticated") {
    return children;
  }

  if (phase === "error") {
    return (
      <main className="mx-auto flex min-h-screen max-w-xl items-center px-6 py-12">
        <section className="w-full space-y-4 rounded-xl border bg-card p-6">
          <div role="alert" className="space-y-2">
            <h1 className="text-xl font-semibold">第三方登录失败</h1>
            <p className="text-sm text-muted-foreground">
              自动重新授权后仍未能建立登录会话，请检查认证服务或稍后重试。
            </p>
          </div>
          <Button
            onClick={() => {
              window.sessionStorage.removeItem(OAUTH_RETRY_KEY);
              setPhase("redirecting");
              redirect(LOGIN_URL);
            }}
          >
            重新登录
          </Button>
        </section>
      </main>
    );
  }

  const message =
    phase === "exchanging"
      ? "正在完成第三方登录"
      : phase === "redirecting"
        ? "正在跳转到认证服务"
        : "正在检查登录状态";

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <p role="status" className="text-sm text-muted-foreground">
        {message}
      </p>
    </main>
  );
}
