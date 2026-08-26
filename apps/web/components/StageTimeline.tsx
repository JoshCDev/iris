import type { PlotStatus } from "@/lib/api";
import { STAGE_META, STAGE_ORDER } from "@/lib/format";

export function StageTimeline({ status }: { status: PlotStatus }) {
  const currentIdx = Math.max(0, STAGE_ORDER.indexOf(status.stage as (typeof STAGE_ORDER)[number]));
  return (
    <div className="stage-timeline" aria-label="Growth-stage timeline">
      {STAGE_ORDER.map((slug, i) => {
        const meta = STAGE_META[slug];
        const state = i < currentIdx ? "is-past" : i === currentIdx ? "is-current" : "";
        return (
          <span key={slug} className={`stage-chip ${state}`} {...(i === currentIdx ? { "aria-current": "step" as const } : {})}>
            <span>{meta.label}{i === currentIdx ? " ●" : ""}</span>
            <small>{meta.days} · {meta.trigger}</small>
          </span>
        );
      })}
    </div>
  );
}
