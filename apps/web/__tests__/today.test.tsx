import { useEffect, type ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RecommendationCard } from "@/components/RecommendationCard";
import { WeatherStateCard } from "@/components/WeatherStateCard";
import { LocaleProvider, useLocale } from "@/lib/i18n";
import type { TodayPayload } from "@/lib/api/v1";

const today: TodayPayload = {
  plot: { id: 4, name: "Petak Utara", is_demo: false },
  freshness: { state: "current", last_observed_at: "2026-08-30T07:15:00+07:00" },
  water: { level_cm: -15.2, source: "manual", stage: "veg_awd", stage_days: 30 },
  weather: { source: "BMKG", adm4: null, availability: "fresh", rain72_mm: 6.5,
             fetched_at: "2026-08-30T07:00:00+07:00", window_end: null,
             stale_since: null, secondary_review: { needs_review: false } },
  recommendation: { id: 913, action: "IRRIGATE", reason_codes: ["AWD_TRIGGER_REACHED"],
                    ruleset_version: "safe-awd-v1", needs_review: false,
                    confirmation_state: "pending" },
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

function renderEn(node: ReactNode) {
  return render(
    <LocaleProvider>
      <En>{node}</En>
    </LocaleProvider>,
  );
}

describe("RecommendationCard", () => {
  it("shows action, reason, and recommendation-only note", () => {
    renderEn(<RecommendationCard today={today} />);
    expect(screen.getByText(/irrigat/i)).toBeInTheDocument();
    expect(screen.getByText(/recommendation only/i)).toBeInTheDocument();
    expect(screen.getByText(/confirm/i)).toBeInTheDocument();
  });
});

describe("WeatherStateCard", () => {
  it("shows availability and rain total", () => {
    renderEn(<WeatherStateCard today={today} />);
    // The BMKG source is its own <strong>; the state label also contains
    // "BMKG", so match the source element exactly.
    expect(screen.getByText("BMKG")).toBeInTheDocument();
    expect(screen.getByText(/6\.5/)).toBeInTheDocument();
  });

  it("never shows a zero rain value when unavailable", () => {
    const unavailableWeather: TodayPayload["weather"] = {
      ...today.weather,
      availability: "unavailable",
      rain72_mm: null,
    };
    const unavailable = {
      ...today,
      weather: unavailableWeather,
    };
    renderEn(<WeatherStateCard today={unavailable} />);
    expect(screen.queryByText(/0 mm/)).not.toBeInTheDocument();
    // "unavailable" appears in both the state label and the freshness
    // fallback span, so assert it is shown at least once.
    expect(screen.getAllByText(/unavailable/i).length).toBeGreaterThan(0);
  });
});
