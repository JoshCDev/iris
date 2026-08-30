// apps/web/__tests__/chart-a11y.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LevelChart } from "@/components/LevelChart";

const readings = [
  { ts: "2026-08-30T07:00:00+07:00", dist_cm: 45, level_cm: -15, batt_v: 3.9 },
  { ts: "2026-08-30T07:15:00+07:00", dist_cm: 44, level_cm: -14, batt_v: 3.9 },
  { ts: "2026-08-30T07:30:00+07:00", dist_cm: 40, level_cm: -10, batt_v: 3.9 },
];

describe("LevelChart", () => {
  it("provides a text summary and a data table", () => {
    render(<LevelChart readings={readings} />);
    expect(screen.getByText(/latest/i)).toBeInTheDocument();
    expect(screen.getByText(/minimum/i)).toBeInTheDocument();
    expect(screen.getByText(/table/i, { selector: "summary" })).toBeInTheDocument();
  });
});
