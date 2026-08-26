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
  DEMO_PLOT_ID,
  getHistory,
  getStatus,
  getVisionReports,
  type PlotHistory,
  type PlotStatus,
  type VisionReportRow,
} from "@/lib/api";

interface PlotBundle {
  status: PlotStatus | null;
  history: PlotHistory | null;
  reports: VisionReportRow[];
  error: string | null;
  refresh: () => void;
}

const PlotContext = createContext<PlotBundle | null>(null);

export function PlotProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<PlotStatus | null>(null);
  const [history, setHistory] = useState<PlotHistory | null>(null);
  const [reports, setReports] = useState<VisionReportRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    Promise.all([
      getStatus(DEMO_PLOT_ID),
      getHistory(DEMO_PLOT_ID, 3),
      getVisionReports(),
    ])
      .then(([s, h, r]) => {
        setStatus(s);
        setHistory(h);
        setReports(r.reports);
        setError(null);
      })
      .catch(() => {
        setError("Cannot reach the data server. Try again shortly.");
      });
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 30_000);
    return () => clearInterval(t);
  }, [refresh]);

  const value = useMemo(
    () => ({ status, history, reports, error, refresh }),
    [status, history, reports, error, refresh],
  );

  return <PlotContext.Provider value={value}>{children}</PlotContext.Provider>;
}

export function usePlot(): PlotBundle {
  const ctx = useContext(PlotContext);
  if (!ctx) {
    throw new Error("usePlot must be used within PlotProvider");
  }
  return ctx;
}

export function latestReport(reports: VisionReportRow[]): VisionReportRow | null {
  return reports[0] ?? null;
}
