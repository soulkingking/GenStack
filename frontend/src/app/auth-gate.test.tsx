import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { exchangeAuthorizationCode, getSession, LOGIN_URL } from "@/api/auth";
import { AuthGate } from "@/app/auth-gate";

vi.mock("@/api/auth", () => ({
  exchangeAuthorizationCode: vi.fn(),
  getSession: vi.fn(),
  LOGIN_URL: "/api/auth/login",
}));

const retryKey = "genstack_oauth_retry";

function setLocation(path: string) {
  window.history.replaceState({}, "", path);
}

describe("AuthGate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.sessionStorage.clear();
    setLocation("/");
  });

  it("renders protected content for an existing session", async () => {
    vi.mocked(getSession).mockResolvedValue({ authenticated: true });

    render(
      <AuthGate>
        <p>受保护内容</p>
      </AuthGate>,
    );

    expect(await screen.findByText("受保护内容")).toBeInTheDocument();
    expect(exchangeAuthorizationCode).not.toHaveBeenCalled();
  });

  it("redirects an unauthenticated request without a code", async () => {
    vi.mocked(getSession).mockResolvedValue({ authenticated: false });
    const redirect = vi.fn();

    render(
      <AuthGate redirect={redirect}>
        <p>受保护内容</p>
      </AuthGate>,
    );

    await waitFor(() => expect(redirect).toHaveBeenCalledWith(LOGIN_URL));
    expect(screen.queryByText("受保护内容")).not.toBeInTheDocument();
  });

  it("exchanges callback parameters, cleans the URL, and renders content", async () => {
    setLocation("/?code=callback-code&state=callback-state&keep=1#section");
    vi.mocked(getSession).mockResolvedValue({ authenticated: false });
    vi.mocked(exchangeAuthorizationCode).mockResolvedValue({ authenticated: true });
    const replaceUrl = vi.fn();

    render(
      <AuthGate replaceUrl={replaceUrl}>
        <p>受保护内容</p>
      </AuthGate>,
    );

    expect(await screen.findByText("受保护内容")).toBeInTheDocument();
    expect(exchangeAuthorizationCode).toHaveBeenCalledWith(
      "callback-code",
      "callback-state",
    );
    expect(replaceUrl).toHaveBeenCalledWith("/?keep=1#section");
    expect(window.sessionStorage.getItem(retryKey)).toBeNull();
  });

  it("restarts authorization after the first exchange failure", async () => {
    setLocation("/?code=expired-code&state=callback-state");
    vi.mocked(getSession).mockResolvedValue({ authenticated: false });
    vi.mocked(exchangeAuthorizationCode).mockRejectedValue(new Error("exchange failed"));
    const redirect = vi.fn();

    render(
      <AuthGate redirect={redirect}>
        <p>受保护内容</p>
      </AuthGate>,
    );

    await waitFor(() => expect(redirect).toHaveBeenCalledWith(LOGIN_URL));
    expect(window.sessionStorage.getItem(retryKey)).toBe("1");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows an error instead of looping after a repeated failure", async () => {
    setLocation("/?code=invalid-code&state=callback-state");
    window.sessionStorage.setItem(retryKey, "1");
    vi.mocked(getSession).mockResolvedValue({ authenticated: false });
    vi.mocked(exchangeAuthorizationCode).mockRejectedValue(new Error("exchange failed"));
    const redirect = vi.fn();

    render(
      <AuthGate redirect={redirect}>
        <p>受保护内容</p>
      </AuthGate>,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("第三方登录失败");
    expect(redirect).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "重新登录" }));

    expect(window.sessionStorage.getItem(retryKey)).toBeNull();
    expect(redirect).toHaveBeenCalledWith(LOGIN_URL);
  });
});
