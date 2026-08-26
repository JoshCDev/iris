"use client";

import Link from "next/link";
import { DemoBadge } from "@/components/DemoBadge";
import { Icon } from "@/components/Icon";
import { ActionPill } from "@/components/StatusPill";
import { latestReport, usePlot } from "@/lib/PlotContext";
import {
  askLeafHref,
  askWhyHref,
  classLabelId,
  fmtLevel,
  fmtNum,
  fmtTs,
  irrigationNoteEn,
  reasonEn,
  STAGE_META,
} from "@/lib/format";

interface AlertItem {
  tone: "risk" | "warn";
  title: string;
  detail: string;
}

export function LiveStatusStrip() {
  const { status, history, reports, error } = usePlot();
  const leaf = latestReport(reports);

  if (error) {
    return (
      <div className="plot-card plot-card--flat" role="status">
        <div className="callout callout--warning">
          <strong>Cannot reach the data server.</strong> Try again shortly.
        </div>
      </div>
    );
  }

  const alerts: AlertItem[] = [];
  if (status?.action === "IRRIGATE") {
    alerts.push({
      tone: "risk",
      title: "Irrigation due now",
      detail: reasonEn(status.reason_id),
    });
  }
  const batts = (history?.readings ?? [])
    .map((r) => r.batt_v)
    .filter((v): v is number => v !== null);
  const minBatt = batts.length > 0 ? Math.min(...batts) : null;
  if (minBatt !== null && minBatt < 3.6) {
    alerts.push({
      tone: "warn",
      title: `Sensor node battery low (${fmtNum(minBatt, 2)} V)`,
      detail: "Schedule a battery swap or solar-panel check.",
    });
  }
  for (const r of reports.slice(0, 10)) {
    if (r.fusion?.risk_level === "high") {
      alerts.push({
        tone: "risk",
        title: `High combined risk: ${classLabelId(r.top_class)}`,
        detail: irrigationNoteEn(r.fusion.irrigation_note) ?? "",
      });
    }
  }

  return (
    <div className="plot-card">
      <div className="plot-card__head">
        <span className="plot-card__name">
          <Icon name="pin" size={20} />
          {status ? status.name : "Demo plot"}
        </span>
        <span className="plot-card__flags">
          {status?.is_demo && <DemoBadge small />}
          {status && <ActionPill action={status.action} />}
        </span>
      </div>

      <dl className="plot-card__stats">
        <div>
          <dt>Water level</dt>
          <dd>{status ? fmtLevel(status.level_cm) : "n/a"}</dd>
        </div>
        <div>
          <dt>Growth stage</dt>
          <dd>{status ? STAGE_META[status.stage]?.label ?? status.stage : "n/a"}</dd>
          <small>d {status?.stage_days ?? "n/a"}</small>
        </div>
        <div>
          <dt>Rain 72 h</dt>
          <dd>{status ? `${fmtNum(status.rain72_mm)} mm` : "n/a"}</dd>
        </div>
        <div>
          <dt>Last leaf</dt>
          <dd>{leaf ? classLabelId(leaf.top_class) : "none yet"}</dd>
          <small>{leaf ? fmtTs(leaf.ts) : "upload on Leaf"}</small>
        </div>
      </dl>

      <div className="plot-card__alerts">
        {!status ? (
          <p className="muted small">Loading plot status…</p>
        ) : alerts.length === 0 ? (
          <p className="small muted plot-card__clear">
            <Icon name="check-circle" size={20} /> No active alerts.
          </p>
        ) : (
          alerts.slice(0, 2).map((a, i) => (
            <div key={i} className={`alert-line${a.tone === "risk" ? " alert-line--risk" : " alert-line--warn"}`}>
              <Icon name={a.tone === "risk" ? "alert-triangle" : "clock"} size={20} />
              <span>
                <strong>{a.title}</strong>
                {a.detail && <span className="small">{a.detail}</span>}
              </span>
            </div>
          ))
        )}
      </div>

      <div className="plot-card__links">
        <Link href="/water" className="plot-card__link">
          Water →
        </Link>
        <Link href="/health" className="plot-card__link">
          Leaf →
        </Link>
        <Link href={status ? askWhyHref(status.action) : "/assistant"} className="plot-card__link">
          Ask →
        </Link>
        {leaf && (
          <Link href={askLeafHref(leaf.top_class)} className="plot-card__link plot-card__link--quiet">
            About the leaf
          </Link>
        )}
      </div>
    </div>
  );
}
