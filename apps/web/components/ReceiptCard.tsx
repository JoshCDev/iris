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
      <div className="impact-dual" aria-label="Impact figures with two labels">
        <div className="impact-dual__col">
          <p className="impact-dual__kicker">This prototype [simulated]</p>
          <p className="impact-dual__lead">E3 water-balance on this repo</p>
          <ul>
            <li>Water −37.5% (8,000 → 5,000 m³ ha⁻¹)</li>
            <li>CH₄ −10.8% (0.378 t CO₂e)</li>
            <li>Not field measurements</li>
          </ul>
        </div>
        <div className="impact-dual__col impact-dual__col--lit">
          <p className="impact-dual__kicker">Literature aggregate [field]</p>
          <p className="impact-dual__lead">Multi-site trials, not this plot</p>
          <ul>
            <li>Water: mild AWD −23.4% (Carrijo 2017); adoption up to −38% (Lampayan 2015)</li>
            <li>CH₄: mild AWD −49.4%; overall −51.6%; ≤3 drying events −40.6% (Zhao 2024)</li>
            <li>Those cuts need deeper drying than this simulation</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
