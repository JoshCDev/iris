"use client";

import { useState } from "react";
import Link from "next/link";
import type { TodayPayload } from "@/lib/api/v1";
import { postV1Confirmation } from "@/lib/api/v1";
import { useLocale } from "@/lib/i18n";
import { actionVerb, fmtLevel, fmtNum, fmtTs } from "@/lib/format";
import { Icon } from "@/components/Icon";

export function RecommendationCard({ today }: { today: TodayPayload }) {
  const { t } = useLocale();
  const rec = today.recommendation;
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  if (!rec) {
    return (
      <div className="card" role="status">
        <strong>{t("common.loading")}</strong>
      </div>
    );
  }

  const confirm = async (status: "performed" | "deferred" | "declined") => {
    setBusy(true);
    setNote(null);
    try {
      await postV1Confirmation(rec.id, { status });
      setNote(t(status === "performed" ? "records.confirmed" : "records.recommended"));
    } catch {
      setNote(t("common.error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card card--strong recommendation-card">
      <div className="recommendation-card__head">
        <Icon name={rec.action === "IRRIGATE" ? "droplet" : "clock"} size={24} aria-hidden="true" />
        <h2>{actionVerb(rec.action)}</h2>
        {rec.needs_review && <span className="status-pill status-pill--alert">review</span>}
      </div>
      <p className="recommendation-card__reason">
        {rec.reason_codes[0] ?? rec.action}
      </p>
      <dl className="plot-card__stats">
        <div><dt>Water</dt><dd>{fmtLevel(today.water.level_cm)}</dd></div>
        <div><dt>Stage</dt><dd>{today.water.stage}</dd></div>
        <div><dt>Observed</dt><dd>{fmtTs(today.freshness.last_observed_at)}</dd></div>
        <div><dt>Source</dt><dd>{today.water.source ?? "n/a"}</dd></div>
      </dl>
      <p className="small muted">
        {t("today.recommendationOnly")}{" "}
        <Link href="/records">{t("nav.records")} →</Link>
      </p>
      <div className="recommendation-card__actions">
        <button type="button" className="button button--primary" disabled={busy} onClick={() => confirm("performed")}>
          {t("today.confirm")}
        </button>
        <button type="button" className="button button--secondary" disabled={busy} onClick={() => confirm("deferred")}>
          {t("today.defer")}
        </button>
        <button type="button" className="button button--secondary" disabled={busy} onClick={() => confirm("declined")}>
          {t("today.decline")}
        </button>
      </div>
      {note && <p className="small" role="status">{note}</p>}
    </div>
  );
}
