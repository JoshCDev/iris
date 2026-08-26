// Typed wrappers for the pinned IRIS backend contracts (all same-origin via
// the next.config rewrite /api/* → http://localhost:8000/api/*).

export const DEMO_PLOT_NAME = "Sawah Demo - Salatiga";
export const DEMO_PLOT_ID = 1;

// ── Shapes (pinned) ───────────────────────────────────────────────────────

export interface PlotStatus {
  plot_id: number;
  name: string;
  level_cm: number | null;
  stage: string;
  stage_days: number;
  action: string | null;
  reason_id: string | null;
  rain72_mm: number | null;
  next_check: string | null;
  last_ts: string | null;
  is_demo: boolean;
}

export interface Reading {
  ts: string;
  dist_cm: number;
  level_cm: number;
  batt_v: number | null;
}

export interface Decision {
  ts: string;
  stage: string;
  level_cm: number;
  action: string;
  reason_id: string;
  rain72_mm: number | null;
}

export interface PlotHistory {
  plot_id: number;
  name: string;
  days: number;
  readings: Reading[];
  decisions: Decision[];
}

export interface GreenReceipt {
  plot_id: number;
  label: string;
  season_days: number;
  flooded_days: number;
  aerated_days: number;
  sf_w_effective: number;
  water_baseline_m3: number;
  water_actual_m3: number;
  water_saved_m3: number;
  water_saved_pct: number;
  ch4_baseline_kg: number;
  ch4_actual_kg: number;
  ch4_saved_kg: number;
  co2e_saved_t: number;
  text: string;
  claim_source?: "e3_backtest" | "plot_window";
  claim_note?: string;
}

export type RiskLevel = "low" | "medium" | "high";

export interface FusionResult {
  risk_level: RiskLevel;
  drivers_id: string[];
  drivers_en: string[];
  irrigation_note?: string | null;
}

export interface VisionPrediction {
  report_id: number;
  top_class: string;
  class_label_id: string;
  class_label_en: string;
  confidence: number;
  severity: string;
  advisory_id: string;
  advisory_en: string;
  fusion: FusionResult | null;
  is_demo: boolean;
}

export interface VisionReportRow {
  report_id: number;
  ts: string;
  plot_id: number | null;
  top_class: string;
  confidence: number;
  severity: string;
  language: string;
  fusion: FusionResult | null;
  is_demo: boolean;
}

export interface VisionReportsResponse {
  reports: VisionReportRow[];
}

export interface WeatherForecast {
  rain72_mm: number;
  stale: boolean;
}

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
  image_ref?: string;
}

export interface ToolHop {
  tool: string;
  args_summary: string;
  ms: number;
}

export interface ChatResponse {
  reply: string;
  tool_trace: ToolHop[];
  mode: "live" | "offline";
}

export interface HealthStatus {
  status: string;
  db: string;
  onnx: string;
  llm: string;
  mode: string;
}

export interface SeedSummary {
  plot_id: number;
  name: string;
  readings: number;
  decisions: number;
  irrigations: number;
  hold_for_rain: number;
  vision_reports: number;
  replaced_plots: number;
  is_demo: boolean;
}

// ── Errors ────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number, code = "error") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

interface ErrorBody {
  code?: string;
  detail?: unknown;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, init);
  } catch {
    throw new ApiError(
      "Cannot reach the data server. Try again shortly.",
      0,
      "network_error",
    );
  }
  if (!res.ok) {
    let body: ErrorBody = {};
    try {
      body = (await res.json()) as ErrorBody;
    } catch {
      // non-JSON error body
    }
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : Array.isArray(body.detail)
          ? JSON.stringify(body.detail)
          : `HTTP ${res.status}`;
    const code = typeof body.code === "string" ? body.code : "http_error";
    throw new ApiError(detail, res.status, code);
  }
  return (await res.json()) as T;
}

// ── Endpoints ─────────────────────────────────────────────────────────────

export function getHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/health");
}

export function getStatus(plotId: number): Promise<PlotStatus> {
  return request<PlotStatus>(`/plots/${plotId}/status`);
}

export function getHistory(plotId: number, days: number): Promise<PlotHistory> {
  return request<PlotHistory>(`/plots/${plotId}/history?days=${days}`);
}

export function getReceipt(plotId: number, seasonDays = 100): Promise<GreenReceipt> {
  return request<GreenReceipt>(`/plots/${plotId}/receipt?season_days=${seasonDays}&claim=e3`);
}

export function postIngest(body: {
  device_plot_name: string;
  dist_cm: number;
  batt_v?: number;
}): Promise<PlotStatus> {
  return request<PlotStatus>("/ingest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getWeather(): Promise<WeatherForecast> {
  return request<WeatherForecast>("/weather/forecast");
}

export function postVisionPredict(input: {
  file: File;
  plotId?: number;
  language?: "id" | "en";
}): Promise<VisionPrediction> {
  const form = new FormData();
  form.append("image", input.file);
  if (input.plotId !== undefined) form.append("plot_id", String(input.plotId));
  form.append("language", input.language ?? "en");
  return request<VisionPrediction>("/vision/predict", { method: "POST", body: form });
}

export function getVisionReports(): Promise<VisionReportsResponse> {
  return request<VisionReportsResponse>("/vision/reports");
}

export function postChat(body: {
  session_id: string;
  messages: ChatMessage[];
}): Promise<ChatResponse> {
  return request<ChatResponse>("/assistant/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function postDemoSeed(): Promise<SeedSummary> {
  return request<SeedSummary>("/demo/seed", { method: "POST" });
}
