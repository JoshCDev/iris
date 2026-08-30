import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { PlotProvider, usePlot } from "@/lib/PlotContext";
import * as v1 from "@/lib/api/v1";

function Probe() {
  const { activePlotId, plots, today } = usePlot();
  return (
    <div>
      <span data-testid="plot-id">{activePlotId ?? "none"}</span>
      <span data-testid="plot-count">{plots.length}</span>
      <span data-testid="today-action">{today?.recommendation?.action ?? "none"}</span>
    </div>
  );
}

describe("PlotProvider", () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(v1, "getV1Plots").mockResolvedValue({
      plots: [{ id: 7, name: "Petak Utara", is_demo: false }],
    });
    vi.spyOn(v1, "getV1Today").mockResolvedValue({
      plot: { id: 7, name: "Petak Utara", is_demo: false },
      freshness: { state: "current", last_observed_at: null },
      water: { level_cm: -5, source: "manual", stage: "veg_awd" },
      weather: { source: "BMKG", adm4: null, availability: "fresh",
                 rain72_mm: 0, fetched_at: null, window_end: null,
                 stale_since: null, secondary_review: { needs_review: false } },
      recommendation: { id: 1, action: "WAIT", reason_codes: ["SAFE"],
                        ruleset_version: "safe-awd-v1", needs_review: false,
                        confirmation_state: "pending" },
      latest_leaf: null,
    });
    vi.spyOn(v1, "getV1WaterHistory").mockResolvedValue({
      plot_id: 7, observations: [], recommendations: [], total: 0,
    });
  });

  it("selects the first plot and loads today", async () => {
    render(<PlotProvider><Probe /></PlotProvider>);
    await waitFor(() => expect(screen.getByTestId("plot-id").textContent).toBe("7"));
    expect(screen.getByTestId("plot-count").textContent).toBe("1");
    await waitFor(() => expect(screen.getByTestId("today-action").textContent).toBe("WAIT"));
  });

  it("retries getV1Plots when the initial load fails", async () => {
    vi.mocked(v1.getV1Plots)
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce({
        plots: [{ id: 7, name: "Petak Utara", is_demo: false }],
      });
    render(<PlotProvider><Probe /></PlotProvider>);
    await waitFor(() => expect(screen.getByTestId("plot-id").textContent).toBe("7"));
    expect(screen.getByTestId("plot-count").textContent).toBe("1");
    expect(v1.getV1Plots).toHaveBeenCalledTimes(2);
  });
});
