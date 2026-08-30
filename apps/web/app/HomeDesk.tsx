"use client";

import Link from "next/link";
import { DemoBadge } from "@/components/DemoBadge";
import { FreshnessBanner } from "@/components/FreshnessBanner";
import { RecommendationCard } from "@/components/RecommendationCard";
import { WeatherStateCard } from "@/components/WeatherStateCard";
import { usePlot } from "@/lib/PlotContext";
import { useLocale } from "@/lib/i18n";
import { askLeafHref, askWhyHref, classLabelId, fmtTs } from "@/lib/format";
import { HomeFacets } from "./HomeClient";

export function HomeDesk() {
  const { today, activePlot } = usePlot();
  const { t } = useLocale();

  if (!today) {
    return (
      <section className="section">
        <div className="page-shell" role="status">
          <p className="small muted">{t("common.loading")}</p>
        </div>
      </section>
    );
  }

  const plotName = activePlot?.name ?? today.plot.name;
  const isDemo = activePlot?.is_demo ?? today.plot.is_demo;
  const leaf = today.latest_leaf;

  return (
    <>
      <section className="section section--compact">
        <div className="page-shell grid">
          <div>
            <p className="section-kicker">{t("today.kicker")}</p>
            <h1 className="page-title">{plotName}</h1>
            {isDemo && <DemoBadge />}
          </div>
          <FreshnessBanner today={today} />
          <RecommendationCard today={today} />
          <WeatherStateCard today={today} />
          {leaf && (
            <div className="card">
              <div className="plot-card__head">
                <h3>Latest leaf</h3>
                <Link href="/health" className="plot-card__link">
                  Leaf →
                </Link>
              </div>
              <p>
                {classLabelId(leaf.class ?? "none")}
                {leaf.severity ? ` — ${leaf.severity}` : ""}
              </p>
              <p className="small muted">{fmtTs(leaf.created_at)}</p>
            </div>
          )}
        </div>
      </section>

      <section className="section section--compact">
        <div className="page-shell">
          <HomeFacets
            askHref={today.recommendation ? askWhyHref(today.recommendation.action) : "/assistant"}
            leafHref={askLeafHref(leaf?.class)}
          />
          <div className="cross-strip">
            <Link href="/records">{t("nav.records")} →</Link>
          </div>
        </div>
      </section>

      <section className="section section--compact">
        <div className="page-shell">
          <div className="card">
            <h3>{t("today.evidenceCard")}</h3>
            <p className="small muted">
              Simulation, public-dataset benchmark, and literature context sit apart from live plot status.
            </p>
            <Link href="/evidence">{t("nav.evidence")} →</Link>
          </div>
        </div>
      </section>
    </>
  );
}
