import { getCurrentUser } from "@/api/current-user";

describe("current user API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads whitelisted user fields with same-origin credentials", async () => {
    const user = {
      user_id: 1,
      username: "admin",
      real_name: "管理员",
      dept_id: 2,
      dept_name: "平台部",
      company_id: 3,
      roles: ["admin"],
      permissions: ["system:read"],
      menu_permissions: [],
      role_permissions: [],
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(user), {
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getCurrentUser()).resolves.toEqual(user);
    expect(fetchMock).toHaveBeenCalledWith("/api/current-user", {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
  });

  it("rejects unsuccessful responses with the HTTP status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 401 })),
    );

    await expect(getCurrentUser()).rejects.toThrow(
      "Request failed with status 401",
    );
  });
});
