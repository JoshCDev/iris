import type { Metadata } from "next";
import { HealthClient } from "./HealthClient";

export const metadata: Metadata = {
  title: "Leaf | IRIS",
  description:
    "Leaf-photo check on the active plot, scored against water level and weather.",
};

export default function HealthPage() {
  return (
    <section className="section">
      <div className="page-shell" style={{ display: "grid", gap: 22 }}>
        <div className="section-heading" style={{ marginBottom: 0 }}>
          <div>
            <p className="section-kicker">This plot · leaf</p>
            <h1 className="page-title">Canopy anomaly</h1>
            <p className="section-copy" style={{ marginTop: 12 }}>
              The photo is classified, then crossed with this plot&apos;s water.
              A disease class without water status is not a decision. A person
              confirms; IRIS does not diagnose.
            </p>
          </div>
        </div>
        <HealthClient />
        <div className="callout callout--warning">
          AI screening is not a diagnosis. Confirm the final call with an
          extension officer (human in the loop). Low-confidence photographs
          are rejected rather than guessed.
        </div>
      </div>
    </section>
  );
}
