// apps/web/lib/api/v1.ts
// Typed v1 client — the only layer the frontend consumes (WEBAPP_SPEC §10.4).
import { request } from "@/lib/api";

export interface PlotSummary {
  id: number;
  name: string;
  is_demo: boolean;
}

export interface WeatherState {
  source: string;
  adm4: string | null;
  availability: "fresh" | "stale-cache" | "unavailable";
  rain72_mm: number | null;
  fetched_at: string | null;
  window_end: string | null;
  stale_since: string | null;
  secondary_review: { needs_review: boolean };
  hitl?: {
    bmkg_rain72_mm: number;
    bmkg_wet: boolean;
    logreg_p_wet: number;
    logreg_wet: boolean;
    needs_review: boolean;
    note: string;
  } | null;
}

export interface Recommendation {
  id: number;
  action: string;
  reason_codes: string[];
  ruleset_version: string;
  needs_review: boolean;
  confirmation_state: "pending" | "confirmed";
}

export interface TodayPayload {
  plot: PlotSummary;
  freshness: { state: string; last_observed_at: string | null };
  water: { level_cm: number | null; source: string | null; stage: string };
  weather: WeatherState;
  recommendation: Recommendation | null;
  latest_leaf: {
    id: number; class: string | null; confidence: number | null;
    severity: string | null; evidence_type: string; created_at: string;
  } | null;
}

export interface WaterObservationRow {
  id: number; level_cm: number; source: string;
  observed_at: string; received_at: string;
  quality_state: string; demo: boolean;
}

export interface WaterHistory {
  plot_id: number;
  observations: WaterObservationRow[];
  recommendations: Recommendation[];
  total: number;
}

export interface ActionConfirmation {
  id: number;
  recommendation_id: number;
  status: "performed" | "deferred" | "declined" | "corrected";
  action_at: string | null;
  volume_m3: number | null;
  note: string | null;
  created_at: string;
  demo: boolean;
}

export interface EvidenceE3 {
  evidence_type: string;
  label: string;
  title: string;
  assumptions: { season_days: number; area_ha: number; rain_mm: number; drawdown_cm_per_day: number };
  values: Record<string, number>;
  disclosures: string[];
  source_version: string;
  calculation_version: string;
  generated_at: string;
}

export interface EvidenceVision {
  evidence_type: string;
  label: string;
  title: string;
  n: number;
  accuracy: number;
  macro_f1: number;
  model_version: string;
  field_validation: string;
  note: string;
  source_version: string;
  calculation_version: string;
  generated_at: string;
}

export interface HealthReady {
  status: string;
  db: string;
}

export function getV1Plots(): Promise<{ plots: PlotSummary[] }> {
  return request<{ plots: PlotSummary[] }>("/v1/plots");
}

export function getV1Today(plotId: number): Promise<TodayPayload> {
  return request<TodayPayload>(`/v1/plots/${plotId}/today`);
}

export function postV1WaterObservation(
  plotId: number,
  body: { level_cm: number; source?: string; observed_at?: string; actor?: string },
): Promise<TodayPayload> {
  return request<TodayPayload>(`/v1/plots/${plotId}/water-observations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getV1WaterHistory(
  plotId: number,
  opts: { limit?: number; offset?: number } = {},
): Promise<WaterHistory> {
  const q = new URLSearchParams();
  if (opts.limit) q.set("limit", String(opts.limit));
  if (opts.offset) q.set("offset", String(opts.offset));
  const qs = q.toString();
  return request<WaterHistory>(`/v1/plots/${plotId}/water-history${qs ? `?${qs}` : ""}`);
}

export function postV1Confirmation(
  recommendationId: number,
  body: { status: string; note?: string; volume_m3?: number | null; action_at?: string },
): Promise<{ recommendation: Recommendation; confirmations: ActionConfirmation[] }> {
  return request(`/v1/recommendations/${recommendationId}/confirmations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getV1Recommendation(
  recommendationId: number,
): Promise<{ recommendation: Recommendation; confirmations: ActionConfirmation[] }> {
  return request(`/v1/recommendations/${recommendationId}`);
}

export function getV1Weather(plotId: number): Promise<WeatherState> {
  return request<WeatherState>(`/v1/plots/${plotId}/weather`);
}

export function getV1EvidenceE3(): Promise<EvidenceE3> {
  return request<EvidenceE3>("/v1/evidence/e3");
}

export function getV1EvidenceVision(): Promise<EvidenceVision> {
  return request<EvidenceVision>("/v1/evidence/vision");
}

export function getV1HealthReady(): Promise<HealthReady> {
  return request<HealthReady>("/v1/health/ready");
}
