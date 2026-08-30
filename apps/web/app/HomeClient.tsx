"use client";

import Link from "next/link";
import { PillarCard } from "@/components/PillarCard";

export function HomeFacets({ askHref, leafHref }: { askHref: string; leafHref: string }) {
  return (
    <div className="grid grid--3">
      <PillarCard
        icon="droplet"
        title="Water"
        desc="Water-level sensing and rain-aware AWD rules for this plot. The pipe is the safety constraint; rain may hold irrigation, not drain a shallow pond."
        href="/water"
        cta="Open water"
        proof={
          <span className="pillar-card__figure">
            Irrigation guidance
            <small>Recorded levels and rules on Water</small>
          </span>
        }
      />
      <PillarCard
        icon="camera"
        title="Leaf"
        desc="A leaf photograph is classified, then scored against this plot's water and weather. The class alone is not an irrigation decision."
        href="/health"
        cta="Check leaf"
        proof={<span className="pill pill--warn">Photo × plot water</span>}
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
            <span className="chat-mini__a">Answered from water level, rain, and leaf class when present.</span>
            <Link className="chat-mini__tool" href={leafHref}>
              Or ask about the leaf →
            </Link>
          </span>
        }
      />
    </div>
  );
}
