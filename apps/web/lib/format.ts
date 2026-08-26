import type { RiskLevel } from "./api";

const _WIB_FMT = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Jakarta",
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

export function fmtTs(ts: string | null | undefined): string {
  if (!ts) return "n/a";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return `${_WIB_FMT.format(d)} WIB`;
}

export function fmtNum(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined) return "n/a";
  return n.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function fmtInt(n: number | null | undefined): string {
  if (n === null || n === undefined) return "n/a";
  return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

export function fmtLevel(levelCm: number | null | undefined): string {
  if (levelCm === null || levelCm === undefined) return "n/a";
  return `${fmtNum(levelCm)} cm`;
}

export const ACTION_META: Record<string, { label: string; tone: "default" | "alert" | "danger" }> = {
  WAIT: { label: "Safe (wait)", tone: "default" },
  HOLD_FOR_RAIN: { label: "Hold for rain", tone: "alert" },
  IRRIGATE: { label: "Irrigate now", tone: "danger" },
};

export function actionMeta(action: string | null): { label: string; tone: "default" | "alert" | "danger" } {
  if (!action) return { label: "No data yet", tone: "alert" };
  return ACTION_META[action] ?? { label: action, tone: "default" };
}

export const ACTION_VERB: Record<string, string> = {
  WAIT: "Hold irrigation",
  HOLD_FOR_RAIN: "Hold for rain",
  IRRIGATE: "Irrigate now",
};

export function actionVerb(action: string | null): string {
  if (!action) return "Waiting for a sensor reading";
  return ACTION_VERB[action] ?? action;
}

export const STAGE_ORDER = [
  "establishment",
  "veg_awd",
  "flowering_lock",
  "grain_fill_awd",
  "harvest",
] as const;

export interface StageMeta {
  slug: string;
  label: string;
  days: string;
  trigger: string;
}

export const STAGE_META: Record<string, StageMeta> = {
  establishment: { slug: "establishment", label: "Establishment", days: "d 0–13", trigger: "flood ≥ +5 cm" },
  veg_awd: { slug: "veg_awd", label: "Vegetative (AWD)", days: "d 14–54", trigger: "trigger −15 cm" },
  flowering_lock: { slug: "flowering_lock", label: "Flowering (must flood)", days: "d 55–79", trigger: "flood ≥ +3 cm" },
  grain_fill_awd: { slug: "grain_fill_awd", label: "Grain fill (AWD)", days: "d 80–99", trigger: "trigger −15 cm" },
  harvest: { slug: "harvest", label: "Harvest", days: "≥ d 100", trigger: "drain the field" },
};

export const SEVERITY_TONE: Record<string, "low" | "medium" | "high" | "urgent"> = {
  Low: "low",
  Moderate: "medium",
  High: "high",
  "Urgent Review": "urgent",
};

export const SEVERITY_PCT: Record<string, number> = {
  Low: 25,
  Moderate: 50,
  High: 75,
  "Urgent Review": 100,
};

export function severityTone(sev: string): "low" | "medium" | "high" | "urgent" {
  return SEVERITY_TONE[sev] ?? "medium";
}

export function severityLabel(sev: string): string {
  const map: Record<string, string> = {
    ringan: "Low",
    sedang: "Moderate",
    berat: "High",
    Low: "Low",
    Moderate: "Moderate",
    High: "High",
    "Urgent Review": "Urgent Review",
  };
  return map[sev] ?? sev;
}

export const severityLabelId = severityLabel;

export function riskLabel(risk: RiskLevel): string {
  return risk === "high" ? "High" : risk === "medium" ? "Medium" : "Low";
}

export function classLabelId(slug: string): string {
  const map: Record<string, string> = {
    blast: "Blast",
    brown_spot: "Brown spot",
    tungro: "Tungro",
    bacterial_leaf_blight: "Bacterial leaf blight (BLB)",
    healthy: "Healthy",
    none: "No symptoms",
  };
  return map[slug] ?? slug;
}

export function askWhyQuestion(action: string | null | undefined): string {
  if (action === "IRRIGATE") return "Why irrigate now?";
  if (action === "HOLD_FOR_RAIN") return "Why is irrigation on hold?";
  return "When does this plot need irrigation?";
}

export function askWhyHref(action: string | null | undefined): string {
  return `/assistant?q=${encodeURIComponent(askWhyQuestion(action))}`;
}

export function askLeafQuestion(classSlug: string | null | undefined): string {
  if (!classSlug) return "What is the latest leaf status on this plot?";
  return `What does ${classLabelId(classSlug)} mean for this plot's water?`;
}

export function askLeafHref(classSlug: string | null | undefined): string {
  return `/assistant?q=${encodeURIComponent(askLeafQuestion(classSlug))}`;
}

/** Map stored scheduler sentences (ID or EN) to English for display. */
export function reasonEn(reason: string | null | undefined): string {
  if (!reason) return "No decision yet.";
  const patterns: [RegExp, string][] = [
    [
      /^Kondisi aman \((.+); pemicu (.+)\)\. Pantau(?: kembali dalam)? 15 menit(?: berikutnya)?\.$/,
      "Safe ($1; trigger $2). Check again in 15 minutes.",
    ],
    [/^Menunggu hujan: prakiraan (.+) mm dalam 72 jam\.$/, "Holding for rain: $1 mm forecast in 72 h."],
    [
      /^Fase pembungaan: sawah wajib tergenang \(≥ \+3 cm\) agar hasil tidak turun\.$/,
      "Flowering lock: keep the field flooded (≥ +3 cm) to protect yield.",
    ],
    [
      /^Ambang safe-AWD tercapai \((.+) cm\)\. Irigasi hingga \+(.+) cm\.$/,
      "Safe-AWD trigger reached ($1 cm). Irrigate to +$2 cm.",
    ],
    [
      /^Musim tanam selesai: sawah dapat ditiriskan untuk panen\.$/,
      "Season complete: the field can be drained for harvest.",
    ],
  ];
  for (const [re, repl] of patterns) {
    if (re.test(reason)) return reason.replace(re, repl);
  }
  return reason;
}

export function irrigationNoteEn(note: string | null | undefined): string | null {
  if (!note) return null;
  const map: Record<string, string> = {
    "pertimbangkan siklus AWD lebih pendek": "consider a shorter AWD cycle",
    "kelola air secara terputus (intermittent), hindari aliran antarpetakan":
      "use intermittent water; avoid flow between plots",
    "lanjutkan pemantauan berkala": "continue routine monitoring",
  };
  return map[note] ?? note;
}
