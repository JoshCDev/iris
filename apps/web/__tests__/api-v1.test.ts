// apps/web/__tests__/api-v1.test.ts
import { describe, expect, it, vi, beforeEach } from "vitest";
import {
  getV1Today,
  getV1Plots,
  postV1Confirmation,
  type TodayPayload,
} from "@/lib/api/v1";

const todayFixture: TodayPayload = {
  plot: { id: 4, name: "Petak Utara", is_demo: false },
  freshness: { state: "current", last_observed_at: "2026-08-30T07:15:00+07:00" },
  water: { level_cm: -15.2, source: "manual", stage: "veg_awd", stage_days: 30 },
  weather: { source: "BMKG", adm4: null, availability: "fresh", rain72_mm: 6.5,
             fetched_at: "2026-08-30T07:00:00+07:00", window_end: "2026-09-02T07:00:00+07:00",
             stale_since: null, secondary_review: { needs_review: false } },
  recommendation: { id: 913, action: "IRRIGATE", reason_codes: ["AWD_TRIGGER_REACHED"],
                    ruleset_version: "safe-awd-v1", needs_review: false,
                    confirmation_state: "pending" },
  latest_leaf: null,
};

describe("api/v1", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("getV1Today hits /api/v1/plots/{id}/today", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true, json: async () => todayFixture,
    } as Response);
    const out = await getV1Today(4);
    expect(out.plot.name).toBe("Petak Utara");
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/plots/4/today", undefined);
  });

  it("getV1Plots returns summaries", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true, json: async () => ({ plots: [{ id: 1, name: "Sawah Demo - Salatiga", is_demo: true }] }),
    } as Response);
    const out = await getV1Plots();
    expect(out.plots[0].is_demo).toBe(true);
  });

  it("postV1Confirmation posts status", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true, json: async () => ({ recommendation: {}, confirmations: [] }),
    } as Response);
    await postV1Confirmation(913, { status: "performed", note: "done" });
    const [, init] = fetchMock.mock.calls[0];
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toMatchObject({ status: "performed", note: "done" });
  });
});
