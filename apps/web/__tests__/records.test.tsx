// apps/web/__tests__/records.test.tsx
import { useEffect, type ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RecordsClient } from "@/app/records/RecordsClient";
import { LocaleProvider, useLocale } from "@/lib/i18n";
import { PlotContext } from "@/lib/PlotContext";
import type { TodayPayload } from "@/lib/api/v1";

const today: TodayPayload = {
  plot: { id: 4, name: "Petak Utara", is_demo: false },
  freshness: { state: "current", last_observed_at: null },
  water: { level_cm: -5, source: "manual", stage: "veg_awd" },
  weather: { source: "BMKG", adm4: null, availability: "fresh", rain72_mm: 0,
             fetched_at: null, window_end: null, stale_since: null,
             secondary_review: { needs_review: false } },
  recommendation: { id: 913, action: "IRRIGATE", reason_codes: ["AWD_TRIGGER_REACHED"],
                    ruleset_version: "safe-awd-v1", needs_review: false,
                    confirmation_state: "confirmed" },
  latest_leaf: null,
};

// The brief's assertions are English copy, but LocaleProvider defaults to
// Indonesian (Task 3.4 catalogue). Force the en locale so the brief's
// assertions are deterministically satisfiable.
function En({ children }: { children: ReactNode }) {
  const { setLocale } = useLocale();
  useEffect(() => setLocale("en"), [setLocale]);
  return <>{children}</>;
}

describe("RecordsClient", () => {
  it("distinguishes recommended from confirmed", () => {
    render(
      <LocaleProvider>
        <En>
          <PlotContext.Provider
            value={{
              status: null,
              // Legacy transition field (Task 3.3): always null in the
              // bundle; RecordsClient fetches its own v1 WaterHistory.
              history: null,
              reports: [],
              error: null,
              refresh: () => {},
              plots: [],
              activePlotId: 4,
              activePlot: null,
              today,
              selectPlot: () => {},
            }}
          >
            <RecordsClient />
          </PlotContext.Provider>
        </En>
      </LocaleProvider>,
    );
    expect(screen.getByText(/confirmed/i)).toBeInTheDocument();
    expect(screen.getByText(/recommended/i)).toBeInTheDocument();
  });
});
