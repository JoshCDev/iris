import { render, screen } from "@testing-library/react";
import { act } from "react";
import { HomeFacets } from "@/app/HomeClient";
import { PlotContext } from "@/lib/PlotContext";
import * as api from "@/lib/api";
import { describe, expect, it, vi } from "vitest";

const status = {
  plot_id: 1, name: "Sawah Demo - Salatiga", level_cm: -8, stage: "veg_awd",
  stage_days: 30, action: "WAIT", reason_id: "Safe", rain72_mm: 0,
  next_check: null, last_ts: null, is_demo: true,
};

const history = {
  plot_id: 1,
  name: "Sawah Demo - Salatiga",
  days: 3,
  readings: [
    { ts: "2026-08-30T10:00:00Z", dist_cm: 118, level_cm: -8, batt_v: 4.1 },
    { ts: "2026-08-30T11:00:00Z", dist_cm: 116, level_cm: -6, batt_v: 4.1 },
    { ts: "2026-08-30T12:00:00Z", dist_cm: 115, level_cm: -5, batt_v: 4.1 },
  ],
  decisions: [],
};

// Force the claim-rendering path: getReceipt must RESOLVE with an
// e3_backtest receipt, the exact scenario that used to render
// "N% water saved". Under the pre-removal code the real fetch rejects in
// jsdom and the old `.catch(() => {})` swallowed it, leaving receipt null
// and the UI on "Seasonal water-saving estimate" — which contains no
// "water saved" substring, so the original test passed before AND after
// the removal. Resolving the mock makes a re-added claim fail the test.
vi.spyOn(api, "getReceipt").mockResolvedValue({
  plot_id: 1,
  label: "Sawah Demo - Salatiga",
  season_days: 100,
  flooded_days: 61,
  aerated_days: 39,
  sf_w_effective: 0.6,
  water_baseline_m3: 1240,
  water_actual_m3: 1091,
  water_saved_m3: 149,
  water_saved_pct: 12,
  ch4_baseline_kg: 60.5,
  ch4_actual_kg: 46.2,
  ch4_saved_kg: 14.3,
  co2e_saved_t: 0.4,
  text: "E3 backtest over the last 100 days",
  claim_source: "e3_backtest",
});

describe("HomeFacets", () => {
  it("never asserts a water-saving percentage on Today", async () => {
    render(
      <PlotContext.Provider value={{ status, history, reports: [], error: null, refresh: vi.fn() }}>
        <HomeFacets askHref="/assistant" leafHref="/assistant" />
      </PlotContext.Provider>,
    );
    // Flush the receipt effect: drain the microtask queue so the mocked
    // getReceipt resolution would have rendered "12% water saved" by now
    // if the claim path were still present. Asserting only after this
    // flush is what makes the guard meaningful.
    await act(async () => {});
    expect(screen.queryByText(/water saved/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/%\s*water saved/i)).not.toBeInTheDocument();
  });
});
