# IRIS Demo Script: 10-Minute Stage Runbook

> Audience: jury / professor demo, one presenter (+ optional operator).
> Everything runs locally: FastAPI on `:8000`, Next.js on `:3000`.
> Honesty rule applies on stage: every receipt number is `[simulated]`; vision
> results are "AI-assisted triage - bukan diagnosis laboratorium".

## Setup checklist (do BEFORE the session)

1. **Seed first** (idempotent - safe to re-run):
   ```powershell
   cd C:\xampp\htdocs\iris-platform\apps\api
   ..\..\.venv\Scripts\python.exe scripts\seed_demo.py
   ```
   Expect: plot **"Sawah Demo - Salatiga"**, 2880 readings (30 d × 96/day @15 min),
   ~7 irrigations, ~100 HOLD_FOR_RAIN decisions, 2 demo vision reports.
2. **Start backend** (from `apps\api`):
   `..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000`
3. **Set key** (only if you want the LIVE LLM beat): `$env:DEEPSEEK_API_KEY="sk-..."`
   in the SAME terminal before starting uvicorn. No key? The demo still works  - 
   assistant answers offline with a visible badge.
4. **Start frontend** (production build - stable on stage):
   `cd apps\web ; npm run build ; npm run start` → open <http://localhost:3000>.
5. **Sanity check**: `/api/health` shows `onnx:"loaded"`, `db:"ok"`, and
   `llm/mode` = `reachable|unreachable` / `live|offline` (never scaffold strings).
6. **Have ready**: phone with a rice-leaf photo (or any leaf), plus the bundled
   samples on `/health` as lighting-proof fallback.
7. Do NOT kill processes between rehearsal and show - ports 8000/3000 stay warm;
   if you need extra instances use ports ≥ 8040.

---

## 0:00 - Landing page (`/`)

Open <http://localhost:3000>. Hero = tindakan air petak aktif + kartu
status hidup + tiga sisi petak (Air / Daun / Tanya), bukan tiga produk.

Say: *"IRIS - Intelligent Rice Integrated System. Satu petak, satu loop:
AWD sadar hujan, triase anomali kanopi, dan asisten yang hanya boleh
mengutip catatan petak yang sama."*

Point at the **plot bar under the header** and the **live plot card**  - 
real data from the seeded plot, DEMO badge visible. Framing: *"Dari pipa
manual ke keputusan otomatis - air, daun, dan tanya mengikuti petak yang
sama."*

## 1:30 - Air (`/water`)

Walk through top-to-bottom:

- **Sawtooth chart**: level oscillates between **+5 cm (refill)** and the red
  dashed **−15 cm AWD trigger**. Each tooth = one safe-AWD cycle: drawdown by
  seepage+evapotranspiration (with diurnal noise), refill when trigger hits.
- **Rain-hold story (seed days 18–19)**: point at the deeper dip (~−25 cm).
  For two days the forecast said 22 mm/72 h, so instead of irrigating at −15
  the engine issued **HOLD_FOR_RAIN** (hard floor −25 cm protects the crop),
  then refilled. *"Mesin tidak hanya membaca pipa - dia membaca langit."*
- **Flowering lock**: use the stage timeline chips - establishment → veg_awd →
  **flowering_lock** (day 55–80) → grain_fill. Explain: from day 55 the field
  MUST stay flooded (≥ 0 band shaded on the chart); the scheduler hard-locks
  irrigation there regardless of AWD triggers. *"Saat pembungaan, hasil lebih
  mahal dari air."* (The seeded window shows days 0–30; lock behavior is shown
  by the timeline + shaded flooded band.)
- **Receipt card**: read the **E3 pinned numbers** (not the 30-day demo window):
  > *"Resi hijau klaim musim - backtest E3, label [simulated]: hemat air
  > 37,5% (8.000 → 5.000 m³/ha), SF_w efektif 0,8922, CH₄ dihindari 14,01 kg
  > ≈ 0,378 ton CO₂e. Petak demo 30 hari tidak dipakai untuk klaim musim."*
  Optional: press **"Simulasi pembacaan sensor (demo)"** once - a synthetic
  reading flows through the REAL decision engine and the big next-action verb
  updates. That button does **not** change the E3 receipt numbers.

## 3:30 - Daun (`/health`) - foto juri live

1. Ask the judge for a phone photo of any leaf (or use your prepared one).
2. Drag-drop it into the upload box → **real ONNX path**: quality guard
   (blank/solid/non-leaf rejection) → MobileNetV3-Large triage → severity +
   bilingual advisory. Same code path as every other image - no demo shortcut.
3. Result card: class (e.g. *Blast*), confidence %, severity bucket
   (Rendah/Sedang/Tinggi/Perlu tinjauan segera), advisory in Indonesian,
   footer disclaimer:
   *"Triase AI bukan diagnosis laboratorium - keputusan pestisida tetap lewat penyuluh."*
4. **Fusion banner**: because `plot_id` is attached, vision × hydrology × weather
   fuse into one explainable risk banner (e.g. risk medium:
   *"Genangan menaikkan kelembapan kanopi…"* or high when deep-dry × brown spot).
   This is the originality centerpiece - say so in one sentence.
5. **If lighting/projector makes the live photo ugly**: click a bundled sample
   button instead (blast fixture classifies at ~99.9% confidence on CPU) and
   keep moving - never fight the light on stage.

## 5:30 - Tanya (`/assistant`)

Three beats, each shows the **"Bagaimana jawaban ini dibuat" trace panel**
under the reply - open it once to show the labeled steps:

1. Status question - type: *"Kapan sawah saya perlu diairi?"*
   → panel step `Mengakses data → status petak` → grounded answer with the
   live level/action.
   Point at the panel: *"Jawaban hanya boleh mengutip hasil tool - tidak ada
   angka karangan."*
2. KB question - type: *"Kenapa metana turun?"*
   → panel step `Mencari basis pengetahuan` → answer citing the KB file
   (`[Sumber: awd-dasar.md]`): AWD menambah hari aerobik → metanogen aktif
   lebih sedikit.
3. Multimodal - attach the same leaf photo: *"Apa penyakit pada foto ini?"*
   → steps `Memeriksa foto daun` + `Menilai risiko gabungan` → triage summary
   fused with the plot's water state + triage-not-diagnosis note.

**Offline toggle demo (the safety story):**
Stop uvicorn (Ctrl+C), clear the key and restart:

```powershell
Remove-Item Env:DEEPSEEK_API_KEY -ErrorAction SilentlyContinue
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

Ask anything again → reply arrives tagged **[mode offline]** with the offline
badge, answers from TF-IDF retrieval over the Indonesian KB, **and still
appends the last-plot status one-liner** (level, fase, tindakan) even when
retrieval misses.
*"Demo tidak bisa mati - saat jaringan LLM putus, petani tetap dapat jawaban
berbasis pengetahuan dan status lahannya."*

## 8:00 - Home hub recap (`/`) + honesty statement

Back on the hub: the plot card + Air / Daun / Tanya recap the same loop;
the header plot bar still shows live water and last leaf. Close with the
honesty statement, verbatim:

> *"Transparansi penuh: data demo diberi label DEMO; resi hijau adalah
> simulasi metode IPCC Tier-1 - belum pengukuran chamber langsung; model
> visi dilatih dari dataset publik Mendeley - validasi lapangan masih
> menyusul. Kami lebih memilih jujur sekarang daripada dikoreksi nanti."*

## 8:45 - Anticipated jury Q&A (one-liners)

- **Why web-first?** Messaging-agnostic adapter keeps the brain channel-free;
  WhatsApp Business API is a planned drop-in next step, not the dependency.
- **Why split ONNX + LLM?** Deterministic eyes (fixed 4-class vision on CPU,
  no hallucinated classes), grounded brain (LLM may only assert what tools
  returned), offline-safe demo (retrieval fallback + visible offline badge).
- **Model accuracy honesty?** We report held-out test-split metrics only; the
  near-perfect validation score on public Mendeley data is a known red flag we
  disclose ourselves; field validation with Indonesian leaves is next.
- **Is CH₄ measured?** Estimated via published IPCC Tier-1 methodology from
  modeled hydrology, stamped `[simulated]`; chamber measurement is future work
  with an agri partner.
- **Originality?** All three components are the team's own prior work (audited
  backend, own rice crop pack); the novelty is the integration - the
  risk-fusion layer joining vision × hydrology × weather, plus per-season
  carbon receipts. PhytoSignal itself is not being re-entered elsewhere.

---

### If wifi dies mid-demo
Vision (ONNX, CPU), irrigation engine, receipts, dashboard: all local - nothing breaks.
Weather forecast fails OPEN (`stale:true`, rain=0). Assistant auto-falls back to
offline mode (badge visible). Only the live-LLM phrasing quality degrades.
