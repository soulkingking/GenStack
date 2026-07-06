import {
  exchangeAuthorizationCode,
  getSession,
  LOGIN_URL,
} from "@/api/auth";

describe("authentication API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads the browser session without exposing token details", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ authenticated: true }), {
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getSession()).resolves.toEqual({ authenticated: true });
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/session", {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
  });

  it("exchanges callback parameters through the same-origin backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ authenticated: true }), {
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(exchangeAuthorizationCode("code", "state")).resolves.toEqual({
      authenticated: true,
    });
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/token", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ code: "code", state: "state" }),
    });
    expect(LOGIN_URL).toBe("/api/auth/login");
  });

  it("rejects unsuccessful and malformed session responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(new Response(null, { status: 502 })),
    );

    await expect(getSession()).rejects.toThrow("Authentication request failed with status 502");

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: "must-not-be-used" })),
      ),
    );

    await expect(getSession()).rejects.toThrow("Invalid authentication response");

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(new Response("not-json")),
    );

    await expect(getSession()).rejects.toThrow("Invalid authentication response");
  });
});
