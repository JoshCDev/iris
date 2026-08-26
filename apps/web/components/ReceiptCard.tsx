import type { GreenReceipt } from "@/lib/api";
import { DemoBadge } from "@/components/DemoBadge";
import { fmtInt, fmtNum } from "@/lib/format";

export function ReceiptCard({ receipt }: { receipt: GreenReceipt }) {
  const isE3 = receipt.claim_source === "e3_backtest";
  return (
    <div className="receipt-card">
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", justifyContent: "space-between" }}>
        <h3>Season green receipt</h3>
        <div className="receipt-card__tags" style={{ marginTop: 0 }}>
          <span className="sim-tag">{isE3 ? "[simulated – E3]" : `label: ${receipt.label}`}</span>
          <DemoBadge small />
        </div>
      </div>
      {receipt.claim_note && (
        <p className="small" style={{ margin: "8px 0 0", lineHeight: 1.5 }}>
          {receipt.claim_note}
        </p>
      )}
      <dl>
        <div>
          <dt>Water saved</dt>
          <dd>
            {fmtNum(receipt.water_saved_pct)}% <small>≈ {fmtInt(receipt.water_saved_m3)} m³</small>
          </dd>
        </div>
        <div>
          <dt>CH₄ avoided</dt>
          <dd>{fmtNum(receipt.ch4_saved_kg)} kg</dd>
        </div>
        <div>
          <dt>CO₂e equivalent</dt>
          <dd>{fmtNum(receipt.co2e_saved_t, 3)} t</dd>
        </div>
        <div>
          <dt>Effective SF_w</dt>
          <dd>{fmtNum(receipt.sf_w_effective, 4)}</dd>
        </div>
        <div>
          <dt>Flooded / aerated days</dt>
          <dd>
            {receipt.flooded_days} / {receipt.aerated_days} <small>of {receipt.season_days} season days</small>
          </dd>
        </div>
        <div>
          <dt>Water: baseline → actual</dt>
          <dd>
            {fmtInt(receipt.water_baseline_m3)} → {fmtInt(receipt.water_actual_m3)} <small>m³</small>
          </dd>
        </div>
      </dl>
      <details>
        <summary>Full receipt text (IPCC Tier-1)</summary>
        <pre>{receipt.text}</pre>
      </details>
    </div>
  );
}
