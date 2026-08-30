"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  getV1Plots,
  getV1Today,
  getV1WaterHistory,
  type PlotSummary,
  type TodayPayload,
} from "@/lib/api/v1";
import type { PlotHistory, PlotStatus, VisionReportRow } from "@/lib/api";

interface PlotBundle {
  // Legacy transition fields — consumers migrate to the v1 fields in
  // Tasks 3.5–3.9. `status` is derived from the v1 `today` payload so
  // existing consumers keep rendering; `history` stays null because v1
  // water observations carry no dist_cm/batt_v to fill the legacy
  // Reading shape; `reports` is an empty list (the Leaf page fetches its
  // own reports via getVisionReports).
  status: PlotStatus | null;
  history: PlotHistory | null;
  reports: VisionReportRow[];
  error: string | null;
  refresh: () => void;
  // New v1 fields — the shared active-plot source of truth (CTX-001).
  plots: PlotSummary[];
  activePlotId: number | null;
  activePlot: PlotSummary | null;
  today: TodayPayload | null;
  selectPlot: (plotId: number) => void;
}

export const PlotContext = createContext<PlotBundle | null>(null);

export function PlotProvider({ children }: { children: ReactNode }) {
  const [plots, setPlots] = useState<PlotSummary[]>([]);
  const [activePlotId, setActivePlotId] = useState<number | null>(null);
  const [today, setToday] = useState<TodayPayload | null>(null);
  const [history, setHistory] = useState<PlotHistory | null>(null);
  const [reports] = useState<VisionReportRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      // The plot list is fetched once on mount; if that initial load failed
      // or came back empty the app would stay stuck on "Loading plot…" until
      // a hard refresh. Re-run it here (before the activePlotId guard, which
      // is exactly the state that gets stuck) so any later refresh self-heals.
      if (plots.length === 0) {
        const res = await getV1Plots();
        setPlots(res.plots);
        if (res.plots.length > 0) {
          setActivePlotId((prev) => prev ?? res.plots[0].id);
        }
      }
      if (activePlotId === null) return;
      const [t] = await Promise.all([
        getV1Today(activePlotId),
        getV1WaterHistory(activePlotId, { limit: 50 }),
      ]);
      setToday(t);
      setHistory(null);
      setError(null);
    } catch {
      setError("Cannot reach the data server. Try again shortly.");
    }
  }, [activePlotId, plots.length]);

  useEffect(() => {
    let alive = true;
    getV1Plots()
      .then((res) => {
        if (!alive) return;
        setPlots(res.plots);
        if (res.plots.length > 0) {
          setActivePlotId((prev) => prev ?? res.plots[0].id);
        }
      })
      .catch(() => {
        if (alive) setError("Cannot reach the data server. Try again shortly.");
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 30_000);
    return () => clearInterval(t);
  }, [refresh]);

  const selectPlot = useCallback((plotId: number) => {
    setActivePlotId(plotId);
  }, []);

  const activePlot = useMemo(
    () => plots.find((p) => p.id === activePlotId) ?? null,
    [plots, activePlotId],
  );

  // Legacy PlotStatus derived from the v1 today payload (CTX-001). The v1
  // payload has no stage_days/next_check, so those stay 0/null until the
  // consumers migrate in Tasks 3.5–3.9.
  const status = useMemo<PlotStatus | null>(() => {
    if (!today) return null;
    return {
      plot_id: today.plot.id,
      name: today.plot.name,
      level_cm: today.water.level_cm,
      stage: today.water.stage,
      stage_days: 0,
      action: today.recommendation?.action ?? null,
      reason_id: today.recommendation?.reason_codes[0] ?? null,
      rain72_mm: today.weather.rain72_mm,
      next_check: null,
      last_ts: today.freshness.last_observed_at,
      is_demo: today.plot.is_demo,
    };
  }, [today]);

  const value = useMemo(
    () => ({
      plots,
      activePlotId,
      activePlot,
      today,
      status,
      history,
      reports,
      error,
      refresh,
      selectPlot,
    }),
    [
      plots,
      activePlotId,
      activePlot,
      today,
      status,
      history,
      reports,
      error,
      refresh,
      selectPlot,
    ],
  );

  return <PlotContext.Provider value={value}>{children}</PlotContext.Provider>;
}

export function usePlot(): PlotBundle {
  const ctx = useContext(PlotContext);
  if (!ctx) throw new Error("usePlot must be used within PlotProvider");
  return ctx;
}

export function latestReport<T extends { ts?: string }>(reports: T[]): T | null {
  return reports[0] ?? null;
}
