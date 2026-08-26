"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { latestReport, usePlot } from "@/lib/PlotContext";
import { actionVerb, askWhyHref, classLabelId, fmtLevel, STAGE_META } from "@/lib/format";

export function PlotBar() {
  const pathname = usePathname();
  const { status, reports, error } = usePlot();
  const leaf = latestReport(reports);

  if (error) {
    return (
      <div className="plot-bar plot-bar--warn" role="status">
        <div className="page-shell plot-bar__inner">Plot data is offline.</div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="plot-bar" role="status">
        <div className="page-shell plot-bar__inner">Loading plot…</div>
      </div>
    );
  }

  return (
    <div className="plot-bar" role="navigation" aria-label="Active plot">
      <div className="page-shell plot-bar__inner">
        <strong className="plot-bar__name">{status.name}</strong>
        <span className="plot-bar__cell">Water {fmtLevel(status.level_cm)}</span>
        <span className="plot-bar__cell">{STAGE_META[status.stage]?.label ?? status.stage}</span>
        <span className="plot-bar__cell plot-bar__action">{actionVerb(status.action)}</span>
        <span className="plot-bar__cell">
          Leaf: {leaf ? classLabelId(leaf.top_class) : "no photo yet"}
        </span>
        {pathname !== "/assistant" && (
          <Link href={askWhyHref(status.action)} className="plot-bar__ask">
            Ask why
          </Link>
        )}
      </div>
    </div>
  );
}
