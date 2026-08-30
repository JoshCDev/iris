import { test, expect } from "@playwright/test";

// §16.5 primary farmer journey — keyboard-only (no mouse input).
//
// Prereq: the FastAPI backend must be running on :8000 with seeded demo
// data, e.g. from apps/api:
//   ..\..\.venv\Scripts\python.exe scripts\seed_demo.py
//   ..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
// Then, from apps/web:
//   npm run test:e2e
// (playwright.config.ts starts the Next dev server on :3000 itself.)
//
// The interactive steps below use page.keyboard only: Tab to focus, Enter
// to submit. Page navigation uses URLs (still keyboard-friendly); the
// brief's skeleton orders "Today first", but the v1 Today payload only
// gains a recommendation once a manual observation exists (the seeder
// fills the legacy readings/decisions tables, not water_observations), so
// the journey records the manual level first and inspects Today after.

test("keyboard-only farmer journey", async ({ page }) => {
  // ── 1. Record manual water level (creates the v1 recommendation) ──
  await page.goto("/water");
  // Manual field-tube entry form (WAT-001): label "Catat tinggi air manual (cm)".
  const level = page.getByLabel("Catat tinggi air manual (cm)");
  await expect(level).toBeVisible();
  await level.focus();
  await page.keyboard.type("-15.2");
  const saved = page.waitForResponse(
    (r) => r.url().includes("/water-observations") && r.request().method() === "POST",
  );
  await page.keyboard.press("Enter"); // submits the form (Simpan)
  // The POST captures a weather snapshot before answering, so wait for the
  // response — navigating away mid-request would drop the observation.
  await saved;
  await expect(level).toHaveValue("");

  // ── 2. Inspect the recommendation (Today) ──
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByText(/hanya rekomendasi/i)).toBeVisible();

  // ── 3. Confirm the outcome (keyboard: Tab to the action, Enter) ──
  await page.getByRole("button", { name: /konfirmasi/i }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("status").filter({ hasText: /dikonfirmasi/i })).toBeVisible();

  // ── 4. Screen a leaf (sample chip via keyboard) ──
  await page.goto("/health");
  await expect(page.getByLabel("Upload a leaf photo")).toBeVisible();
  const blast = page.getByRole("button", { name: /blast/i }).first();
  await blast.focus();
  await page.keyboard.press("Enter"); // runs the ONNX triage on the demo sample
  await expect(page.getByRole("button", { name: "Check leaf" })).toBeDisabled();
  // The result card appears once the triage reply lands.
  await expect(page.getByText("Screening, not a diagnosis.")).toBeVisible();

  // ── 5. Request an explanation (assistant, keyboard-typed question) ──
  await page.goto("/assistant");
  const ask = page.getByLabel("Ask IRIS");
  await expect(ask).toBeVisible();
  await ask.focus();
  await page.keyboard.type("Why this water action?");
  await page.keyboard.press("Enter"); // textarea Enter sends (no Shift)
  const log = page.getByRole("log");
  await expect(log).toBeVisible();
  await expect(log.getByText("Why this water action?")).toBeVisible();
  // The assistant answers (live LLM or offline knowledge base); the reply
  // bubble lands in the log right after the user's.
  await expect(log.locator(".chat-msg")).toHaveCount(2, { timeout: 60_000 });

  // ── 6. View the record (recommended + confirmed) ──
  await page.goto("/records");
  await expect(page.getByRole("heading", { name: /catatan/i })).toBeVisible();
  await expect(page.getByText(/direkomendasikan/i)).toBeVisible();
  await expect(page.getByText(/dikonfirmasi/i)).toBeVisible();
});
