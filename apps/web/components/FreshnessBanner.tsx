"use client";

import type { TodayPayload } from "@/lib/api/v1";
import { useLocale } from "@/lib/i18n";

const STALE_MS = 15 * 60 * 1000;

export function FreshnessBanner({ today }: { today: TodayPayload }) {
  const { t } = useLocale();
  const last = today.freshness.last_observed_at;
  const stale =
    !last ||
    Date.now() - new Date(last).getTime() > STALE_MS ||
    today.weather.availability !== "fresh";

  if (!stale) return null;
  return (
    <div className="callout callout--warning" role="status">
      <strong>{t("today.freshness")}:</strong>{" "}
      {t("today.weatherState")} — {today.weather.availability}
    </div>
  );
}
