"use client";

import type { TodayPayload } from "@/lib/api/v1";
import { useLocale } from "@/lib/i18n";
import { fmtNum } from "@/lib/format";

export function WeatherStateCard({ today }: { today: TodayPayload }) {
  const { t } = useLocale();
  const w = today.weather;
  return (
    <div className="card rain-strip">
      <strong>BMKG</strong>
      <span>{t("today.weatherState")}: {w.availability}</span>
      <span>
        {w.rain72_mm === null
          ? t("today.freshness") + " — " + w.availability
          : `${fmtNum(w.rain72_mm)} mm / 72 jam`}
      </span>
      {w.secondary_review?.needs_review && (
        <span className="status-pill status-pill--alert">
          {t("today.rainCheckReview")}
        </span>
      )}
    </div>
  );
}
