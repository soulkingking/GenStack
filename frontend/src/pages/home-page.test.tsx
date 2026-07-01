import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";

import { HomePage } from "@/pages/home-page";

vi.mock("@/api/system", () => ({
  getHealth: vi.fn().mockResolvedValue({ status: "ok" }),
  getMeta: vi.fn().mockResolvedValue({ name: "GenStack", version: "0.1.0" }),
}));

it("shows application identity and healthy API status", async () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <HomePage />
    </QueryClientProvider>,
  );

  expect(await screen.findByRole("heading", { name: "GenStack" })).toBeInTheDocument();
  expect(await screen.findByText("API 正常")).toBeInTheDocument();
  expect(screen.getByText(/0\.1\.0/)).toBeInTheDocument();
});
