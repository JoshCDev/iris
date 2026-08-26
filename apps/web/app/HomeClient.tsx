"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Icon } from "@/components/Icon";
import { PillarCard } from "@/components/PillarCard";
import { usePlot } from "@/lib/PlotContext";
import { getReceipt, type GreenReceipt } from "@/lib/api";
import { actionVerb, fmtNum } from "@/lib/format";

function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) {
    return <span className="sparkline sparkline--empty">Waiting for sensor data…</span>;
  }
  const w = 220;
  const h = 44;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - 4 - ((v - min) / span) * (h - 8);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  return (
    <svg
      className="sparkline"
      viewBox={`0 0 ${w} ${h}`}
      role="img"
      aria-label="Water-level sparkline, last 12 hours"
    >
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function HomeFacets({ askHref, leafHref }: { askHref: string; leafHref: string }) {
  const { status, history } = usePlot();
  const [receipt, setReceipt] = useState<GreenReceipt | null>(null);

  useEffect(() => {
    let alive = true;
    getReceipt(1, 100)
      .then((r) => {
        if (alive) setReceipt(r);
      })
      .catch(() => {
        /* non-fatal */
      });
    return () => {
      alive = false;
    };
  }, []);

  const last48 = (history?.readings ?? []).slice(-48).map((r) => r.level_cm);

  return (
    <div className="grid grid--3">
      <PillarCard
        icon="droplet"
        title="Water"
        desc={
          status
            ? `Today: ${actionVerb(status.action)}. The scheduler uses this plot's AWD pipe and the 72-hour rain forecast.`
            : "Water-level sensing and rain-aware AWD rules for this plot."
        }
        href="/water"
        cta="Open water"
        proof={
          <>
            <Sparkline values={last48} />
            <span className="pillar-card__figure">
              {receipt?.claim_source === "e3_backtest"
                ? `${fmtNum(receipt.water_saved_pct)}% water saved`
                : "Seasonal water-saving estimate"}
              <small>
                {receipt?.claim_source === "e3_backtest" ? "E3 backtest [simulated]" : "E3 season claim"}
              </small>
            </span>
          </>
        }
      />
      <PillarCard
        icon="camera"
        title="Leaf"
        desc="A leaf photograph is classified, then scored against this plot's water and weather. The class alone is not an irrigation decision."
        href="/health"
        cta="Check leaf"
        proof={
          <span className="vision-mini">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/demo_samples/rice/rice-blast-demo.jpg" alt="" />
            <Icon name="send" size={20} className="vision-mini__arrow" />
            <span className="pill pill--warn">Photo × plot water</span>
          </span>
        }
      />
      <PillarCard
        icon="chat"
        title="Ask"
        desc="The assistant may only cite plot status, leaf results, and sources. Questions follow today's water action or last photo."
        href={askHref}
        cta="Ask why"
        proof={
          <span className="chat-mini">
            <span className="chat-mini__q">Why this water action today?</span>
            <span className="chat-mini__a">Answered from water level, rain, and leaf class when present. Tool steps are listed.</span>
            <Link className="chat-mini__tool" href={leafHref}>
              Or ask about the leaf →
            </Link>
          </span>
        }
      />
    </div>
  );
}
