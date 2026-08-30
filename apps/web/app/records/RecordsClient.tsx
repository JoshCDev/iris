"use client";

import { useCallback, useEffect, useState } from "react";
import { usePlot } from "@/lib/PlotContext";
import {
  getV1Recommendation,
  getV1WaterHistory,
  type ActionConfirmation,
  type WaterHistory,
} from "@/lib/api/v1";
import { useLocale } from "@/lib/i18n";
import { actionVerb, fmtLevel, fmtTs } from "@/lib/format";
import { DemoBadge } from "@/components/DemoBadge";

export function RecordsClient() {
  const { today, activePlot, activePlotId, history } = usePlot();
  const { t } = useLocale();
  const [confirmations, setConfirmations] = useState<ActionConfirmation[]>([]);
  // The context bundle's `history` is the legacy PlotHistory (always null —
  // Task 3.3 transition), so the page fetches its own v1 WaterHistory.
  // Local state + refresh() self-corrects on mount.
  const [rows, setRows] = useState<WaterHistory | null>(null);

  const refresh = useCallback(async () => {
    if (!activePlotId) return;
    try {
      const h = await getV1WaterHistory(activePlotId, { limit: 50 });
      setRows(h);
      if (today?.recommendation) {
        const rec = await getV1Recommendation(today.recommendation.id);
        setConfirmations(rec.confirmations);
      }
    } catch {
      /* keep previous rows */
    }
  }, [activePlotId, today?.recommendation]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const rec = today?.recommendation;

  return (
    <div className="grid">
      {activePlot?.is_demo && <DemoBadge />}
      <div className="card">
        <h2>{t("nav.records")}</h2>
        {rec ? (
          <>
            <p>
              <strong>{t("records.recommended")}:</strong> {actionVerb(rec.action)} —{" "}
              {rec.reason_codes[0] ?? rec.action}
            </p>
            <p>
              <strong>{t("records.confirmed")}:</strong>{" "}
              {confirmations.length > 0
                ? confirmations.map((c) => `${c.status} ${fmtTs(c.created_at)}`).join("; ")
                : t("today.defer")}
            </p>
          </>
        ) : (
          <p className="muted">{t("common.loading")}</p>
        )}
      </div>

      <div className="card">
        <h3>{t("water.manualEntry")}</h3>
        {(rows?.observations ?? []).map((o) => (
          <div key={o.id} className="report-row">
            <strong>{fmtLevel(o.level_cm)}</strong>
            <span className="muted small">{o.source}</span>
            <span className="spacer" />
            <span className="muted small">{fmtTs(o.observed_at)}</span>
          </div>
        ))}
        {(rows?.recommendations ?? []).map((r) => (
          <div key={r.id} className="report-row">
            <strong>{actionVerb(r.action)}</strong>
            <span className="muted small">{r.reason_codes[0]}</span>
            {r.superseded_at && <span className="status-pill">superseded</span>}
            <span className="spacer" />
            <span className="muted small">{fmtTs(r.created_at)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
