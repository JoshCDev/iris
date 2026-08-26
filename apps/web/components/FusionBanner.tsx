import Link from "next/link";
import type { FusionResult } from "@/lib/api";
import { irrigationNoteEn, riskLabel } from "@/lib/format";
import { Icon } from "@/components/Icon";

export function FusionBanner({ fusion }: { fusion: FusionResult }) {
  const drivers = fusion.drivers_en.length > 0 ? fusion.drivers_en : fusion.drivers_id;
  const ask = `/assistant?q=${encodeURIComponent("How do leaf risk and water fuse on this plot?")}`;
  return (
    <div className={`fusion-banner fusion-banner--${fusion.risk_level}`}>
      <div className="fusion-banner__title">
        <span>Plot fusion (water × weather × leaf)</span>
        <span
          className={`pill ${fusion.risk_level === "high" ? "pill--risk" : fusion.risk_level === "medium" ? "pill--warn" : "pill--ok"}`}
        >
          {riskLabel(fusion.risk_level)} risk
        </span>
      </div>
      {drivers.length > 0 && <ul>{drivers.map((d) => <li key={d}>{d}</li>)}</ul>}
      {fusion.irrigation_note && (
        <div className="note">
          <Icon name="droplet" size={20} /> {irrigationNoteEn(fusion.irrigation_note)}
        </div>
      )}
      <div className="fusion-banner__links">
        <Link href="/water">See water action</Link>
        <Link href={ask}>Ask the assistant about this fusion</Link>
      </div>
    </div>
  );
}
