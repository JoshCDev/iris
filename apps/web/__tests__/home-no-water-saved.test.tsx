import { render, screen } from "@testing-library/react";
import { HomeFacets } from "@/app/HomeClient";
import { PlotContext } from "@/lib/PlotContext";
import { describe, expect, it, vi } from "vitest";

const status = {
  plot_id: 1, name: "Sawah Demo - Salatiga", level_cm: -8, stage: "veg_awd",
  stage_days: 30, action: "WAIT", reason_id: "Safe", rain72_mm: 0,
  next_check: null, last_ts: null, is_demo: true,
};

describe("HomeFacets", () => {
  it("never asserts a water-saving percentage on Today", () => {
    render(
      <PlotContext.Provider value={{ status, history: null, reports: [], error: null, refresh: vi.fn() }}>
        <HomeFacets askHref="/assistant" leafHref="/assistant" />
      </PlotContext.Provider>,
    );
    expect(screen.queryByText(/water saved/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/%\s*water saved/i)).not.toBeInTheDocument();
  });
});
