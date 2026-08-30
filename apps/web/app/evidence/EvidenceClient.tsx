// apps/web/app/evidence/EvidenceClient.tsx
"use client";

import { useEffect, useState } from "react";
import { getV1EvidenceE3, getV1EvidenceVision, type EvidenceE3, type EvidenceVision } from "@/lib/api/v1";
import { useLocale } from "@/lib/i18n";
import { fmtInt, fmtNum } from "@/lib/format";

// Static aggregate copy from docs/poster-content.md (Carrijo 2017 /
// Lampayan 2015 / Zhao 2024). Deliberately NOT rendered in IRIS units:
// different studies, units, and conditions — context, not validation.
// EVD-006: kept in its own panel with its own labelled badge, no shared
// unlabeled visual scale with the simulation panel.
const LITERATURE = [
  "Water: mild AWD −23.4% (Carrijo 2017); adoption up to −38% (Lampayan 2015).",
  "CH₄: mild AWD −49.4%; overall −51.6%; ≤3 drying events −40.6% (Zhao 2024).",
  "Those cuts need deeper drying than this simulation.",
];

export function EvidenceClient() {
  const { t } = useLocale();
  const [e3, setE3] = useState<EvidenceE3 | null>(null);
  const [vision, setVision] = useState<EvidenceVision | null>(null);

  useEffect(() => {
    getV1EvidenceE3().then(setE3).catch(() => setE3(null));
    getV1EvidenceVision().then(setVision).catch(() => setVision(null));
  }, []);

  return (
    <div className="grid">
      <section className="card evidence-panel" aria-labelledby="e3-heading">
        <span className="evidence-badge">{e3?.label ?? t("evidence.definedSimulation")}</span>
        <h2 id="e3-heading">{e3?.title ?? t("evidence.definedSimulation")}</h2>
        {e3 && (
          <>
            <p className="small muted">
              {e3.assumptions.season_days} days · {e3.assumptions.area_ha} ha ·{" "}
              {e3.assumptions.rain_mm} mm rain · {e3.assumptions.drawdown_cm_per_day} cm/day
            </p>
            <dl className="plot-card__stats">
              <div><dt>Water</dt><dd>{fmtInt(e3.values.water_cf_m3)} → {fmtInt(e3.values.water_awd_m3)} m³</dd></div>
              <div><dt>Saving</dt><dd>{fmtNum(e3.values.water_saved_pct)}%</dd></div>
              <div><dt>CH₄</dt><dd>{fmtNum(e3.values.ch4_cf_kg)} → {fmtNum(e3.values.ch4_awd_kg)} kg</dd></div>
              <div><dt>CO₂e</dt><dd>{fmtNum(e3.values.co2e_saved_t, 3)} t</dd></div>
            </dl>
            <ul>
              {e3.disclosures.map((d) => <li key={d} className="small muted">{d}</li>)}
            </ul>
          </>
        )}
      </section>

      <section className="card evidence-panel" aria-labelledby="vision-heading">
        <span className="evidence-badge">{vision?.label ?? t("evidence.publicDataset")}</span>
        <h2 id="vision-heading">{vision?.title ?? t("evidence.publicDataset")}</h2>
        {vision && (
          <>
            <dl className="plot-card__stats">
              <div><dt>Accuracy</dt><dd>{fmtNum(vision.accuracy * 100)}%</dd></div>
              <div><dt>n</dt><dd>{fmtInt(vision.n)}</dd></div>
              <div><dt>Macro-F1</dt><dd>{fmtNum(vision.macro_f1, 4)}</dd></div>
              <div><dt>Model</dt><dd>{vision.model_version}</dd></div>
            </dl>
            <p className="small muted">{vision.note}</p>
          </>
        )}
      </section>

      <section className="card evidence-panel" aria-labelledby="lit-heading">
        <span className="evidence-badge">{t("evidence.literature")}</span>
        <h2 id="lit-heading">{t("evidence.literature")}</h2>
        <ul>
          {LITERATURE.map((l) => <li key={l} className="small">{l}</li>)}
        </ul>
      </section>
    </div>
  );
}
