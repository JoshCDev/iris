"use client";

import { useCallback, useMemo, useState, type FormEvent } from "react";
import Link from "next/link";
import { CrossLinks } from "@/components/CrossLinks";
import { DemoBadge } from "@/components/DemoBadge";
import { Icon } from "@/components/Icon";
import { LevelChart } from "@/components/LevelChart";
import { ReceiptCard } from "@/components/ReceiptCard";
import { StageTimeline } from "@/components/StageTimeline";
import { usePlot } from "@/lib/PlotContext";
import { ApiError, getHistory, getReceipt, type GreenReceipt, type PlotHistory, type PlotStatus } from "@/lib/api";
import {
  getV1WaterHistory,
  postV1WaterObservation,
  type WaterHistory,
  type WaterObservationRow,
} from "@/lib/api/v1";
import { useLocale } from "@/lib/i18n";
import {
  actionMeta,
  actionVerb,
  askLeafHref,
  classLabelId,
  fmtInt,
  fmtNum,
  fmtTs,
  reasonEn,
  STAGE_META,
} from "@/lib/format";

export function WaterEntryForm({ plotId, onSaved }: { plotId: number; onSaved: () => void }) {
  const { t } = useLocale();
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const level = Number(value);
    if (value.trim() === "" || Number.isNaN(level) || level < -30 || level > 30) {
      setError(t("water.implausible"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await postV1WaterObservation(plotId, { level_cm: level, source: "manual" });
      setValue("");
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="card" onSubmit={submit} aria-describedby="water-hint">
      <h3>{t("water.manualEntry")}</h3>
      <p id="water-hint" className="small muted">{t("water.levelHint")}</p>
      <div className="chat-inputrow">
        <label htmlFor="water-level">{t("water.manualEntry")} (cm)</label>
        <input
          id="water-level"
          type="number"
          step="0.1"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? "water-error" : "water-hint"}
        />
        <button type="submit" className="button button--primary" disabled={busy}>
          {busy ? t("assistant.sending") : t("water.save")}
        </button>
      </div>
      {error && <p id="water-error" className="callout callout--danger" role="alert">{error}</p>}
    </form>
  );
}

/** Map a v1 observation row to the legacy chart Reading shape. */
function toReading(o: WaterObservationRow): { ts: string; dist_cm: number; level_cm: number; batt_v: number | null } {
  return { ts: o.observed_at, dist_cm: 0, level_cm: o.level_cm, batt_v: null };
}

export function WaterClient() {
  const plot = usePlot();
  const { t } = useLocale();
  const today = plot.today;
  const [history, setHistory] = useState<WaterHistory | null>(null);
  const [legacyHistory, setLegacyHistory] = useState<PlotHistory | null>(null);
  const [receipt, setReceipt] = useState<GreenReceipt | null>(null);
  const [receiptError, setReceiptError] = useState<string | null>(null);
  const [simBusy, setSimBusy] = useState(false);

  const refresh = useCallback(async () => {
    if (plot.activePlotId === null) return;
    try {
      setHistory(await getV1WaterHistory(plot.activePlotId, { limit: 100 }));
    } catch {
      // keep previous rows; the plot context refresh covers errors
    }
    try {
      // Dense 7-day sensor record (demo series). Plotted as the continuous
      // line; the v1 observations (manual/sensor entries) overlay on top.
      setLegacyHistory(await getHistory(plot.activePlotId, 7));
    } catch {
      // non-fatal; the v1 observations alone still render
    }
    try {
      setReceipt(await getReceipt(plot.activePlotId, 100));
      setReceiptError(null);
    } catch (e) {
      setReceipt(null);
      setReceiptError(e instanceof ApiError ? e.message : "Receipt not available.");
    }
  }, [plot.activePlotId]);

  const onSaved = useCallback(() => {
    refresh();
    plot.refresh();
  }, [refresh, plot.refresh]);

  // Demo simulation: post a plausible sensor reading through the same v1
  // path so it lands in the shared water_observations/recommendations records.
  const simulateReading = async () => {
    if (plot.activePlotId === null) return;
    setSimBusy(true);
    try {
      const levelCm = Math.round((5 - Math.random() * 20) * 10) / 10; // +5 … −15 cm
      await postV1WaterObservation(plot.activePlotId, {
        level_cm: levelCm,
        source: "sensor",
      });
      await onSaved();
    } catch {
      // non-fatal; the button remains usable
    } finally {
      setSimBusy(false);
    }
  };

  const water = today?.water;
  const rec = today?.recommendation;
  const weather = today?.weather;
  const readings = history?.observations ?? [];

  // Chart series: the dense legacy 7-day record plus the v1 observations
  // (manual/sensor) overlaid at their true timestamps, deduped and sorted.
  const chartReadings = useMemo(() => {
    const merged = new Map<string, { ts: string; dist_cm: number; level_cm: number; batt_v: number | null }>();
    for (const r of legacyHistory?.readings ?? []) {
      merged.set(r.ts, { ts: r.ts, dist_cm: r.dist_cm, level_cm: r.level_cm, batt_v: r.batt_v });
    }
    // v1 rows win on timestamp ties (they are the authoritative records).
    for (const o of readings) {
      merged.set(o.observed_at, toReading(o));
    }
    return [...merged.values()].sort((a, b) => a.ts.localeCompare(b.ts));
  }, [legacyHistory, readings]);

  return (
    <div className="grid">
      <CrossLinks current="water" />
      {today?.plot.is_demo && (
        <div className="demo-banner">
          <DemoBadge />
          <span>Figures on this page are from the built-in demo plot “{today.plot.name}”, not a production field.</span>
        </div>
      )}

      {/* Manual field-tube entry (WAT-001) — above the status/rain sections, demo simulator stays below */}
      {plot.activePlotId === null ? (
        <div className="card">
          <p className="muted">{t("common.loading")}</p>
        </div>
      ) : (
        <WaterEntryForm plotId={plot.activePlotId} onSaved={onSaved} />
      )}

      {/* Next action + rain strip */}
      <div className="grid grid--2" style={{ alignItems: "stretch" }}>
        <div className="card card--strong" style={{ display: "grid", gap: 12 }}>
          <h3>Next action</h3>
          <p className="small muted" style={{ margin: 0 }}>
            Human in the loop. Recommendation only.
          </p>
          {rec ? (
            <>
              <div className={`next-action__verb next-action__verb--${actionMeta(rec.action).tone}`}>
                {actionVerb(rec.action)}
              </div>
              <p style={{ margin: 0, lineHeight: 1.6 }}>{rec.reason_codes[0] ?? rec.action}</p>
              <div className="small muted">
                Stage: {STAGE_META[water?.stage ?? ""]?.label ?? water?.stage ?? "n/a"} · water{" "}
                {fmtNum(water?.level_cm ?? null)} cm · observed{" "}
                {fmtTs(today?.freshness.last_observed_at)}
                {rec.confirmation_state === "confirmed" ? " · confirmed" : " · pending confirmation"}
              </div>
            </>
          ) : (
            <p className="muted">Loading…</p>
          )}
          <div>
            <button
              type="button"
              className="button button--secondary"
              onClick={simulateReading}
              disabled={simBusy}
            >
              {simBusy ? (
                "Sending…"
              ) : (
                <>
                  <Icon name="play" size={20} /> Simulate a sensor reading (demo)
                </>
              )}
            </button>
            <div className="small muted" style={{ marginTop: 8 }}>
              Test readings go through the same decision engine as a field sensor.
            </div>
            {today?.latest_leaf && (
              <p className="small" style={{ margin: "8px 0 0" }}>
                Last leaf on this plot: {classLabelId(today.latest_leaf.class ?? "none")}.{" "}
                <Link href={askLeafHref(today.latest_leaf.class)}>Ask what it means for water →</Link>
              </p>
            )}
          </div>
        </div>

        <div style={{ display: "grid", gap: 14, alignContent: "start" }}>
          <div className="rain-strip">
            <Icon name="cloud-rain" size={24} aria-hidden="true" />
            <strong>{weather?.rain72_mm === null || weather?.rain72_mm === undefined ? "n/a" : `${fmtNum(weather.rain72_mm)} mm`}</strong>
            <span>72-hour rain total · BMKG · supporting only</span>
            {weather && (
              <span className={`status-pill${weather.availability !== "fresh" ? " status-pill--alert" : ""}`}>
                {weather.availability === "fresh"
                  ? "fresh forecast"
                  : weather.availability === "stale-cache"
                    ? "using stored forecast"
                    : "forecast unavailable"}
              </span>
            )}
          </div>
          {weather?.secondary_review?.needs_review && (
            <div className="callout callout--warning">
              <strong>Human review (rain).</strong> The rain forecast needs a
              second look — check local conditions before relying on it.
            </div>
          )}
          <div className="card">
            <h3>Growth-stage timeline</h3>
            <p className="small muted" style={{ marginTop: 8 }}>
              Stage: {STAGE_META[water?.stage ?? ""]?.label ?? water?.stage ?? "n/a"}
            </p>
            {water && (
              <StageTimeline
                status={{ stage: water.stage, stage_days: 0, plot_id: 0, name: "", level_cm: null, action: null, reason_id: null, rain72_mm: null, next_check: null, last_ts: null, is_demo: false } as PlotStatus}
              />
            )}
          </div>
        </div>
      </div>

      {/* Level trace */}
      <div className="card">
        <div className="section-heading" style={{ marginBottom: 12 }}>
          <h3>7-day water-level trace</h3>
          <span className="small muted">
            {chartReadings.length > 0 ? `${fmtInt(chartReadings.length)} readings` : ""}
          </span>
        </div>
        <LevelChart readings={chartReadings} dataKind={water?.kind ?? null} />
      </div>

      {/* Receipt */}
      <div>
        {receipt ? (
          <ReceiptCard receipt={receipt} />
        ) : (
          <div className="callout callout--warning">
            <strong>Green receipt could not be computed.</strong> {receiptError}
          </div>
        )}
      </div>
    </div>
  );
}