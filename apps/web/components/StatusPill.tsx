import { actionMeta } from "@/lib/format";

export function StatusPill({ label, tone = "default" }: { label: string; tone?: "default" | "alert" | "danger" }) {
  const className =
    tone === "danger"
      ? "status-pill status-pill--danger"
      : tone === "alert"
        ? "status-pill status-pill--alert"
        : "status-pill";
  return <span className={className}>{label}</span>;
}

export function ActionPill({ action }: { action: string | null }) {
  const meta = actionMeta(action);
  return <StatusPill label={meta.label} tone={meta.tone} />;
}
