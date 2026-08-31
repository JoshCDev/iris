// apps/web/__tests__/water-entry.test.tsx
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { WaterEntryForm } from "@/app/water/WaterClient";
import { LocaleProvider } from "@/lib/i18n";
import * as v1 from "@/lib/api/v1";

// Vitest runs with `globals: false`, so @testing-library/react's auto-cleanup
// is not registered; without this the second test would see the first test's
// DOM and its `getByRole("button", { name: /simpan/i })` would match twice.
afterEach(cleanup);

describe("WaterEntryForm", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(v1, "postV1WaterObservation").mockResolvedValue({
      plot: { id: 4, name: "Petak Utara", is_demo: false },
      freshness: { state: "current", last_observed_at: null },
      water: { level_cm: -5, source: "manual", stage: "veg_awd", stage_days: 30 },
      weather: { source: "BMKG", adm4: null, availability: "fresh", rain72_mm: 0,
                 fetched_at: null, window_end: null, stale_since: null,
                 secondary_review: { needs_review: false } },
      recommendation: null,
      latest_leaf: null,
    });
  });

  it("submits a manual level and shows the hint", async () => {
    render(<LocaleProvider><WaterEntryForm plotId={4} onSaved={() => {}} /></LocaleProvider>);
    expect(screen.getByLabelText(/tinggi air/i)).toBeInTheDocument();
    expect(screen.getByText(/positif = genangan/i)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/tinggi air/i), "-15.2");
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));
    await waitFor(() => expect(v1.postV1WaterObservation).toHaveBeenCalledWith(4, { level_cm: -15.2, source: "manual" }));
  });

  it("rejects an empty submit without posting a false 0 cm observation", async () => {
    render(<LocaleProvider><WaterEntryForm plotId={4} onSaved={() => {}} /></LocaleProvider>);
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));
    expect(v1.postV1WaterObservation).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/nilai di luar rentang wajar/i);
  });
});
