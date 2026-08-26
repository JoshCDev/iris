import type { Metadata } from "next";
import { Suspense } from "react";
import { AssistantClient } from "./AssistantClient";

export const metadata: Metadata = {
  title: "Ask | IRIS",
  description: "Assistant over plot status, leaf triage, and the knowledge base.",
};

export default function AssistantPage() {
  return (
    <section className="section section--compact">
      <div className="page-shell" style={{ display: "grid", gap: 14 }}>
        <div className="section-heading" style={{ marginBottom: 0 }}>
          <div>
            <p className="section-kicker">This plot · ask</p>
            <h1 className="page-title">Ask the plot record</h1>
            <p className="section-copy" style={{ marginTop: 8 }}>
              Answers use this plot's water, leaf, and knowledge base. Tool
              steps are listed under each reply. Rain advice is a
              recommendation: BMKG plus a LogReg flag for human review.
            </p>
          </div>
        </div>
        <Suspense fallback={<p className="muted">Loading assistant…</p>}>
          <AssistantClient />
        </Suspense>
      </div>
    </section>
  );
}
