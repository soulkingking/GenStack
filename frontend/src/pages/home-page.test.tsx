import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { getCurrentUser } from "@/api/current-user";
import { getHealth, type Health } from "@/api/system";
import { AuthStateContext, type AuthState } from "@/app/auth-state";
import { HomePage } from "@/pages/home-page";

vi.mock("@/api/system", () => ({
  getHealth: vi.fn().mockResolvedValue({ status: "ok" }),
  getMeta: vi.fn().mockResolvedValue({ name: "GenStack", version: "0.1.0" }),
}));

vi.mock("@/api/current-user", () => ({
  getCurrentUser: vi.fn().mockResolvedValue({
    user_id: 1,
    username: "admin",
    real_name: "管理员",
    dept_id: 2,
    dept_name: "平台部",
    company_id: 3,
    roles: ["admin", "auditor"],
    permissions: [],
    menu_permissions: [],
    role_permissions: [],
  }),
}));

// 只清空调用记录、保留模块工厂里的实现，避免用例间互相污染断言。
beforeEach(() => vi.clearAllMocks());

function renderHomePage(auth: AuthState = { enabled: false }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthStateContext.Provider value={auth}>
        <HomePage />
      </AuthStateContext.Provider>
    </QueryClientProvider>,
  );
}

it("shows application identity and healthy API status", async () => {
  renderHomePage();

  expect(await screen.findByRole("heading", { name: "GenStack" })).toBeInTheDocument();
  expect(await screen.findByText("API 正常")).toBeInTheDocument();
  expect(screen.getByText(/0\.1\.0/)).toBeInTheDocument();
});

it("shows current user information when third-party auth is enabled", async () => {
  renderHomePage({ enabled: true });

  expect(await screen.findByText("当前用户")).toBeInTheDocument();
  expect(await screen.findByText("管理员")).toBeInTheDocument();
  expect(screen.getByText("平台部")).toBeInTheDocument();
  expect(screen.getByText("admin、auditor")).toBeInTheDocument();
});

it("hides the user card and skips the request when auth is disabled", async () => {
  renderHomePage();

  await screen.findByText("API 正常");
  expect(screen.queryByText("当前用户")).not.toBeInTheDocument();
  expect(getCurrentUser).not.toHaveBeenCalled();
});

it("announces status changes to screen readers via a live region", async () => {
  renderHomePage();

  const status = await screen.findByRole("status");
  await waitFor(() => expect(status).toHaveTextContent("API 正常"));
});

it("disables the recheck button and spins the icon while refetching", async () => {
  renderHomePage();
  await screen.findByText("API 正常");

  // 让下一次健康检查保持挂起，模拟进行中的重新检查。
  let resolveHealth!: (value: Health) => void;
  vi.mocked(getHealth).mockImplementationOnce(
    () =>
      new Promise<Health>((resolve) => {
        resolveHealth = resolve;
      }),
  );

  const button = screen.getByRole("button", { name: "重新检查" });
  fireEvent.click(button);

  await waitFor(() => expect(button).toBeDisabled());
  expect(button.querySelector("svg")).toHaveClass("animate-spin");

  resolveHealth({ status: "ok" });

  await waitFor(() => expect(button).toBeEnabled());
  expect(button.querySelector("svg")).not.toHaveClass("animate-spin");
});
