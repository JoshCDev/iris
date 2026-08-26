import type { Metadata } from "next";
import { WaterClient } from "./WaterClient";

export const metadata: Metadata = {
  title: "Water | IRIS",
  description: "AWD action for the active plot: water level, growth stage, and season receipt.",
};

export default function WaterPage() {
  return (
    <section className="section">
      <div className="page-shell" style={{ display: "grid", gap: 22 }}>
        <div className="section-heading" style={{ marginBottom: 0 }}>
          <div>
            <p className="section-kicker">This plot · water</p>
            <h1 className="page-title">Today&apos;s water action</h1>
            <p className="section-copy" style={{ marginTop: 12 }}>
              This is a recommendation. Confirm before irrigating; IRIS does
              not start a pump. The AWD pipe is the safety constraint. The
              72-hour BMKG forecast may only hold irrigation above a hard
              floor. A persistence LogReg flags disagreement for human review
              and never skips irrigation by itself. A shallow AWD flood (leaves
              in air) is left to fall by itself. If the pond is already deep
              (≥ 15 cm), lower toward +5 cm if a drain exists; do not dry to
              the AWD trigger.
            </p>
          </div>
        </div>
        <WaterClient />
      </div>
    </section>
  );
}
