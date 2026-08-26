"use client";

import Link from "next/link";
import { LiveStatusStrip } from "@/components/LiveStatusStrip";
import { latestReport, usePlot } from "@/lib/PlotContext";
import { actionVerb, askLeafHref, askWhyHref, classLabelId } from "@/lib/format";
import { HomeFacets } from "./HomeClient";

export function HomeDesk() {
  const { status, reports } = usePlot();
  const leaf = latestReport(reports);
  const verb = actionVerb(status?.action ?? null);

  return (
    <>
      <section className="hero">
        <div className="page-shell hero__grid">
          <div className="hero__copy">
            <p className="hero__kicker">Active plot</p>
            <h1>{status ? verb : "Plot record"}</h1>
            <p className="lede">
              {status
                ? `${status.name}. AIoT on this plot ends in a smart decision you confirm: water, leaf, and assistant share the same readings. IRIS does not start a pump.`
                : "AIoT sensing on one plot, ending in a smart decision the farmer confirms."}
            </p>
            <div className="hero__actions">
              <Link href="/water" className="button button--primary">
                View water
              </Link>
              <Link href="/health" className="button button--on-dark">
                {leaf ? `Leaf: ${classLabelId(leaf.top_class)}` : "Check leaf"}
              </Link>
              <Link
                href={status ? askWhyHref(status.action) : "/assistant"}
                className="button button--on-dark"
              >
                Ask why
              </Link>
            </div>
          </div>
          <div className="hero__panel">
            <LiveStatusStrip />
          </div>
        </div>
      </section>

      <section className="section section--compact">
        <div className="page-shell">
          <p className="loop-caption">
            The novelty is the closed decision at the end of the loop, not a new AWD protocol.
          </p>
          <HomeFacets askHref={status ? askWhyHref(status.action) : "/assistant"} leafHref={askLeafHref(leaf?.top_class)} />
        </div>
      </section>
    </>
  );
}
