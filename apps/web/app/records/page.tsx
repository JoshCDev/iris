import type { Metadata } from "next";
import { RecordsClient } from "./RecordsClient";

export const metadata: Metadata = { title: "IRIS | Records" };

export default function RecordsPage() {
  return (
    <section className="page-shell">
      <h1>Records</h1>
      <RecordsClient />
    </section>
  );
}
