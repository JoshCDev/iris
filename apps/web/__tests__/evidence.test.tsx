// apps/web/__tests__/evidence.test.tsx
import { useEffect, type ReactNode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { EvidenceClient } from "@/app/evidence/EvidenceClient";
import { LocaleProvider, useLocale } from "@/lib/i18n";
import * as v1 from "@/lib/api/v1";

// The brief's assertions are English copy, but LocaleProvider defaults to
// Indonesian (Task 3.4 catalogue). Force the en locale so the brief's
// assertions are deterministically satisfiable (same pattern as
// records.test.tsx).
function En({ children }: { children: ReactNode }) {
  const { setLocale } = useLocale();
  useEffect(() => setLocale("en"), [setLocale]);
  return <>{children}</>;
}

describe("EvidenceClient", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(v1, "getV1EvidenceE3").mockResolvedValue({
      evidence_type: "simulated", label: "DEFINED SIMULATION",
      title: "IRIS defined scheduler simulation (E3)",
      assumptions: { season_days: 100, area_ha: 1.0, rain_mm: 0, drawdown_cm_per_day: 0.8 },
      values: { water_saved_pct: 37.5, water_cf_m3: 8000, water_awd_m3: 5000,
                ch4_cf_kg: 130, ch4_awd_kg: 115.99, co2e_saved_t: 0.3784 },
      disclosures: ["The -15 cm refill trigger did not activate in vegetative or grain-fill stages during E3."],
      source_version: "backtest_summary.json", calculation_version: "1",
      generated_at: "2026-08-30T00:00:00Z",
    });
    vi.spyOn(v1, "getV1EvidenceVision").mockResolvedValue({
      evidence_type: "public-dataset", label: "PUBLIC-DATASET BENCHMARK",
      title: "Rice-leaf screening model", n: 1621, accuracy: 0.9784,
      macro_f1: 0.9783, model_version: "v0.3", field_validation: "pending",
      note: "Indonesian field validation remains pending.",
      source_version: "vision_test_metrics.json", calculation_version: "1",
      generated_at: "2026-08-30T00:00:00Z",
    });
  });

  it("renders three separate panels with labelled badges", async () => {
    render(
      <LocaleProvider>
        <En>
          <EvidenceClient />
        </En>
      </LocaleProvider>,
    );
    await waitFor(() => expect(screen.getByText(/DEFINED SIMULATION/i)).toBeInTheDocument());
    expect(screen.getByText(/PUBLIC-DATASET BENCHMARK/i)).toBeInTheDocument();
    // Both the badge and the heading render the literature label, so query
    // the panel heading (exactly one) rather than getByText (two matches).
    expect(screen.getByRole("heading", { name: /published field literature/i })).toBeInTheDocument();
    expect(screen.getByText(/37\.5/)).toBeInTheDocument();
    expect(screen.getByText(/1,621/)).toBeInTheDocument();
    expect(screen.getByText(/-15 cm/i)).toBeInTheDocument();
    // EVD-004 pinned values must render at full precision (no fmtNum rounding).
    expect(screen.getByText(/115\.99/)).toBeInTheDocument();
    expect(screen.getByText(/0\.3784/)).toBeInTheDocument();
  });
});
