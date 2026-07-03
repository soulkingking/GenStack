import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { getHealth, type Health } from "@/api/system";
import { HomePage } from "@/pages/home-page";

vi.mock("@/api/system", () => ({
  getHealth: vi.fn().mockResolvedValue({ status: "ok" }),
  getMeta: vi.fn().mockResolvedValue({ name: "GenStack", version: "0.1.0" }),
}));

function renderHomePage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <HomePage />
    </QueryClientProvider>,
  );
}

it("shows application identity and healthy API status", async () => {
  renderHomePage();

  expect(await screen.findByRole("heading", { name: "GenStack" })).toBeInTheDocument();
  expect(await screen.findByText("API 正常")).toBeInTheDocument();
  expect(screen.getByText(/0\.1\.0/)).toBeInTheDocument();
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
