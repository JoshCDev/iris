// apps/web/app/evidence/page.tsx
import type { Metadata } from "next";
import { EvidenceClient } from "./EvidenceClient";

export const metadata: Metadata = { title: "IRIS | Evidence" };

export default function EvidencePage() {
  return (
    <section className="page-shell">
      <h1>Evidence</h1>
      <EvidenceClient />
    </section>
  );
}
