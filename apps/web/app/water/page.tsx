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
              Irrigation uses the AWD pipe, crop stage, and 72-hour rain forecast.
              Leaf class and the assistant read the same decision record.
            </p>
          </div>
        </div>
        <WaterClient />
      </div>
    </section>
  );
}
