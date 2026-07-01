import { getHealth, getMeta } from "@/api/system";

describe("system API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads health", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response('{"status":"ok"}')));

    await expect(getHealth()).resolves.toEqual({ status: "ok" });
  });

  it("rejects unsuccessful metadata responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 503 })));

    await expect(getMeta()).rejects.toThrow("Request failed with status 503");
  });
});
