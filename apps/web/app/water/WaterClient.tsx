"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { CrossLinks } from "@/components/CrossLinks";
import { DemoBadge } from "@/components/DemoBadge";
import { Icon } from "@/components/Icon";
import { LevelChart } from "@/components/LevelChart";
import { ReceiptCard } from "@/components/ReceiptCard";
import { StageTimeline } from "@/components/StageTimeline";
import { latestReport, usePlot } from "@/lib/PlotContext";
import {
  ApiError,
  DEMO_PLOT_ID,
  DEMO_PLOT_NAME,
  getHistory,
  getReceipt,
  getStatus,
  getWeather,
  postIngest,
  type GreenReceipt,
  type PlotHistory,
  type PlotStatus,
  type WeatherForecast,
} from "@/lib/api";
import { postV1WaterObservation } from "@/lib/api/v1";
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
    if (Number.isNaN(level) || level < -30 || level > 30) {
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

export function WaterClient() {
  const plot = usePlot();
  const { t } = useLocale();
  const leaf = latestReport(plot.reports);
  const [status, setStatus] = useState<PlotStatus | null>(null);
  const [history, setHistory] = useState<PlotHistory | null>(null);
  const [receipt, setReceipt] = useState<GreenReceipt | null>(null);
  const [receiptError, setReceiptError] = useState<string | null>(null);
  const [weather, setWeather] = useState<WeatherForecast | null>(null);
  const [simBusy, setSimBusy] = useState(false);
  const [simNote, setSimNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [s, h, w] = await Promise.all([
        getStatus(DEMO_PLOT_ID),
        getHistory(DEMO_PLOT_ID, 7),
        getWeather(),
      ]);
      setStatus(s);
      setHistory(h);
      setWeather(w);
      setError(null);
      try {
        setReceipt(await getReceipt(DEMO_PLOT_ID, 100));
        setReceiptError(null);
      } catch (e) {
        setReceipt(null);
        setReceiptError(e instanceof ApiError ? e.message : "Receipt not available.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load data.");
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 60_000);
    return () => clearInterval(t);
  }, [refresh]);

  // Demo simulation: plausible sawtooth drawdown/refill distance.
  // pipe_zero = 30 cm → level −15…+5 cm ⇔ dist_cm 25…45 m.
  const simulateReading = async () => {
    setSimBusy(true);
    setSimNote(null);
    try {
      const distCm = Math.round((26 + Math.random() * 18) * 10) / 10;
      const battV = Math.round((3.85 + Math.random() * 0.2) * 100) / 100;
      await postIngest({ device_plot_name: DEMO_PLOT_NAME, dist_cm: distCm, batt_v: battV });
      setSimNote(
        `Simulated reading logged (distance ${fmtNum(distCm)} cm, battery ${fmtNum(battV, 2)} V). Processed by the same scheduler as a field sensor.`,
      );
      await refresh();
      plot.refresh();
    } catch (e) {
      setSimNote(e instanceof Error ? `Failed: ${e.message}` : "Simulation failed.");
    } finally {
      setSimBusy(false);
    }
  };

  if (error) {
    return (
      <div className="callout callout--danger">
        <strong>Cannot reach the data server.</strong> Try again shortly.
      </div>
    );
  }

  return (
    <div className="grid">
      <CrossLinks current="water" />
      {status?.is_demo && (
        <div className="demo-banner">
          <DemoBadge />
          <span>Figures on this page are from the built-in demo plot “{status.name}”, not a production field.</span>
        </div>
      )}

      {/* Manual field-tube entry (WAT-001) — above the status/rain sections, demo simulator stays below */}
      {plot.activePlotId === null ? (
        <div className="card">
          <p className="muted">{t("common.loading")}</p>
        </div>
      ) : (
        <WaterEntryForm
          plotId={plot.activePlotId}
          onSaved={() => {
            refresh();
            plot.refresh();
          }}
        />
      )}

      {/* Next action + rain strip */}
      <div className="grid grid--2" style={{ alignItems: "stretch" }}>
        <div className="card card--strong" style={{ display: "grid", gap: 12 }}>
          <h3>Next action</h3>
          <p className="small muted" style={{ margin: 0 }}>
            Human in the loop. Recommendation only.
          </p>
          {status ? (
            <>
              <div className={`next-action__verb next-action__verb--${actionMeta(status.action).tone}`}>
                {actionVerb(status.action)}
              </div>
              <p style={{ margin: 0, lineHeight: 1.6 }}>{reasonEn(status.reason_id)}</p>
              <div className="small muted">
                Stage: {STAGE_META[status.stage]?.label ?? status.stage} · d {status.stage_days} · next check {fmtTs(status.next_check)}
                {status.last_ts ? ` · last reading ${fmtTs(status.last_ts)}` : ""}
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
            {simNote && <div className="callout" style={{ marginTop: 10 }}>{simNote}</div>}
            {leaf && (
              <p className="small" style={{ margin: "8px 0 0" }}>
                Last leaf on this plot: {classLabelId(leaf.top_class)}.{" "}
                <Link href={askLeafHref(leaf.top_class)}>Ask what it means for water →</Link>
              </p>
            )}
          </div>
        </div>

        <div style={{ display: "grid", gap: 14, alignContent: "start" }}>
          <div className="rain-strip">
            <Icon name="cloud-rain" size={24} aria-hidden="true" />
            <strong>{fmtNum(status?.rain72_mm ?? weather?.rain72_mm)} mm</strong>
            <span>72-hour rain total · BMKG · supporting only</span>
            {weather && (
              <span className={`status-pill${weather.stale ? " status-pill--alert" : ""}`}>
                {weather.stale ? "using stored forecast" : "fresh forecast"}
              </span>
            )}
          </div>
          {weather?.hitl && (
            <p className="small muted" style={{ margin: 0, lineHeight: 1.5 }}>
              Persistence LogReg second opinion: P(wet){" "}
              {fmtNum(weather.hitl.logreg_p_wet * 100)}%
              {weather.hitl.logreg_wet ? " (wet)" : " (dry)"}. Scheduler still
              uses BMKG only.
            </p>
          )}
          {weather?.hitl?.needs_review && (
            <div className="callout callout--warning">
              <strong>Human review (rain).</strong> {weather.hitl.note}{" "}
              Persistence LogReg P(wet) {fmtNum(weather.hitl.logreg_p_wet * 100)}%.
              BMKG does not skip irrigation by itself if the pipe is already dry.
            </div>
          )}
          <div className="card">
            <h3>Growth-stage timeline</h3>
            <p className="small muted" style={{ marginTop: 8 }}>
              Day {status?.stage_days ?? "n/a"} after transplant →{" "}
              {status ? STAGE_META[status.stage]?.label ?? status.stage : "…"}
            </p>
            {status && <StageTimeline status={status} />}
          </div>
        </div>
      </div>

      {/* Level trace */}
      <div className="card">
        <div className="section-heading" style={{ marginBottom: 12 }}>
          <h3>7-day water-level trace</h3>
          <span className="small muted">
            {history ? `${fmtInt(history.readings.length)} readings` : ""}
          </span>
        </div>
        <LevelChart readings={history?.readings ?? []} />
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
