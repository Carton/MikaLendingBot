import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChartsPage } from "./ChartsPage";

vi.mock("echarts-for-react", () => ({
  default: () => <div data-testid="echarts" />
}));

describe("ChartsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows an empty state when no history exists", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({}), { status: 200 }))
    );

    render(<ChartsPage />);

    await screen.findByText("No chart history available");
  });

  it("renders chart panels for available history", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ USD: [[100, "1", "10"]] }), { status: 200 }))
    );

    render(<ChartsPage />);

    await waitFor(() => expect(screen.getByTestId("echarts")).toBeInTheDocument());
  });
});
