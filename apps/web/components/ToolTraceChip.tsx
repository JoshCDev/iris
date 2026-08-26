import type { ToolHop } from "@/lib/api";
import { Icon } from "@/components/Icon";

const TOOL_LABEL: Record<string, string> = {
  get_plot_status: "Read plot status",
  get_weather: "Fetch rain forecast",
  run_vision_triage: "Check leaf photo",
  search_kb: "Search knowledge base",
  get_receipt: "Compute green receipt",
  get_risk_fusion: "Score combined risk",
};

export function TracePanel({ hops }: { hops: ToolHop[] }) {
  if (!hops.length) return null;
  return (
    <details className="trace-panel">
      <summary>
        <Icon name="wrench" size={20} />
        How this answer was made · {hops.length} step{hops.length === 1 ? "" : "s"}
      </summary>
      <ol className="trace-panel__list">
        {hops.map((hop, i) => (
          <li key={i}>
            <span>{TOOL_LABEL[hop.tool] ?? hop.tool}</span>
            <small>{hop.ms} ms</small>
          </li>
        ))}
      </ol>
    </details>
  );
}
