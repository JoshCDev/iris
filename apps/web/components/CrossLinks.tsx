"use client";

import Link from "next/link";
import { latestReport, usePlot } from "@/lib/PlotContext";
import { actionVerb, askLeafHref, askWhyHref, classLabelId } from "@/lib/format";

export function CrossLinks({ current }: { current: "water" | "health" | "assistant" }) {
  const { status, reports } = usePlot();
  const leaf = latestReport(reports);

  return (
    <nav className="cross-strip" aria-label="Plot links">
      {current !== "water" && (
        <Link href="/water">Water: {status ? actionVerb(status.action) : "open irrigation"}</Link>
      )}
      {current !== "health" && (
        <Link href="/health">
          Leaf: {leaf ? classLabelId(leaf.top_class) : "check canopy"}
        </Link>
      )}
      {current !== "assistant" && (
        <Link href={current === "health" ? askLeafHref(leaf?.top_class) : askWhyHref(status?.action)}>
          Ask IRIS about this plot
        </Link>
      )}
    </nav>
  );
}
