# Arsitektur IRIS

IRIS adalah platform pertanian presisi tiga pilar dalam satu monorepo:
**Smart AWD** (irigasi hemat air + receipt karbon), **Crop Health Vision**
(deteksi penyakit daun padi dari foto), dan **AI Assistant** (asisten agronomis).
Backend FastAPI (`apps/api`) dan frontend Next.js (`apps/web`) berbagi satu
database SQLite.

## Peta komponen

| Komponen | Lokasi | Peran |
| --- | --- | --- |
| Web dashboard | `apps/web` | Next.js App Router + TypeScript + Tailwind, port 3000; seluruh panggilan `/api/*` di-rewrite sebagai proxy ke FastAPI `:8000` |
| Ingest & decision API | `apps/api` | FastAPI port 8000; menerima pembacaan sensor, menjalankan keputusan **pada saat ingest**, mengekspos status/riwayat/receipt |
| Stage machine AWD (Pilar 1) | `apps/api/app/irrigation/protocol.py` | Fase: establishment <14 hari; veg_awd <55 (pemicu −15 cm); flowering_lock <80 (**wajib genang ≥ +3 cm**); grain_fill_awd <100 (−15 cm); harvest ≥100 |
| Scheduler & rain-skip | `apps/api/app/irrigation/scheduler.py` | Keputusan irigasi: HOLD_FOR_RAIN bila rain72 ≥ 15 mm/72 jam dan level masih di atas hard floor (pemicu −10 cm); establishment & flowering_lock dikecualikan. Jika muka air ≥ 0 cm dan di atas pemicu: WAIT **"Do not drain"** (AWD mengering lewat ET, bukan pompa keluar). `DRAIN` hanya panen |
| Rain HITL (LogReg) | `apps/api/app/irrigation/rain_hitl.py`, `rain_logreg.json` | Opini kedua persistensi/klimatologi vs BMKG. Tidak pernah mengubah `rain72` yang masuk `decide()`. Flag `needs_review` jika basah/kering tidak sama atau P(wet) 0,35–0,65. Dilatih Open-Meteo harian Salatiga (n=3154, akurasi latih 0,59 vs base rate ~0,50) |
| Akuntansi karbon | `apps/api/app/irrigation/ipcc.py` | Receipt IPCC Tier-1: EF 1,30 (Tbl 5.11), SF_w 1/0,78 (Tbl 5.12), GWP 27 (AR6); label `simulated \| measured \| projected` |
| Cuaca | `apps/api/app/irrigation/weather_bmkg.py` + `bmkg_areas.py` | Prakiraan BMKG per kelurahan (`adm4`). Katalog 83.763 kode dari PDF part 1-4 dimuat ke tabel `bmkg_areas`. Default demo: Kelurahan Salatiga `33.73.01.1003` |
| Vision pipeline (Pilar 2) | `apps/api/app/vision/{crop_packs,image_guard,inference,advisory,severity}.py` | Image guard (kualitas + penolakan non-daun; rule tekstur entropy ≥3,0) → inferensi ONNX di CPU → severity + advisory dwibahasa ID/EN |
| Model pack padi | `apps/api/crop_packs/rice/` (`model.onnx`) | MobileNetV3-Large ~16,8 MB; 5 kelas: bacterial_leaf_blight, blast, brown_spot, healthy, tungro (v0.3) |
| Fusion risiko | `apps/api/app/fusion/risk.py` + `fusion_rules.json` | Matriks rule penyakit × awd_state (`flooded/shallow_dry/deep_dry/beyond_trigger/flowering_lock`) × wet_weather (rain72 ≥ 15 mm) → `risk_level` + drivers ID/EN + `irrigation_note` |
| AI Assistant | `apps/api/app/assistant/{agent,tools,prompts,fallback}.py` | DeepSeek Chat Completions (`https://api.deepseek.com`), default `IRIS_LLM_MODEL=deepseek-v4-flash-vision-exp` (experimental vision ID, 21 Aug 2026). Photographs are sent as `image_url` parts; official class from ONNX tool. Max 6 hops, 60 s timeout. |
| Tool asisten | `apps/api/app/assistant/tools.py` | 6 tools: `get_plot_status`, `get_weather`, `run_vision_triage`, `search_kb`, `get_receipt`, `get_risk_fusion` |
| Fallback offline | `apps/api/app/rag.py` + `apps/api/app/kb/*.md` | Retrieval TF-IDF atas knowledge base internal + one-liner status; UI menampilkan badge mode offline |
| Backtest & eksperimen | `experiments/run_all.py` → `experiments/outputs/backtest_summary.json` | E3: 23 vs 100 irigasi, 5000 vs 8000 m³ (−37,5%), CH4 130 → 115,99 kg, 0,3784 t CO2e, sf_w_eff 0,8922 - `[simulated]` |
| Demo seeder | `POST /api/demo/seed` | Plot "Sawah Demo - Salatiga": 2880 pembacaan (30 hari @15 menit), `is_demo=1`, badge DEMO di UI |
| Database | SQLite via `IRIS_DB` (default `apps/api/storage/iris.db`) | Tabel `plots`, `readings`, `decisions`, `irrigations`, `vision_reports`, `chat_messages` (indeks komposit `plot_id + ts`) |
| Konfigurasi | environment | `DEEPSEEK_API_KEY`, `IRIS_LLM_MODEL`, `IRIS_DB`, `IRIS_DEVICE_TOKEN` (opsional), `WEB_ORIGIN`, `BMKG_ADM4` |

Endpoint utama: `POST /api/ingest`, `GET /api/plots/{id}/status|history|receipt`,
`POST /api/vision/predict`, `GET /api/vision/reports`,
`POST /api/assistant/chat`, `GET /api/weather/forecast`, `POST /api/demo/seed`,
`GET /api/health`.

## Aliran data

```mermaid
sequenceDiagram
    participant N as Sensor node
    participant API as FastAPI :8000
    participant W as BMKG
    participant DB as SQLite iris.db
    participant U as Browser petani
    participant NX as Next.js :3000
    participant V as ONNX MobileNetV3
    participant L as DeepSeek LLM

    N->>API: POST /api/ingest (dist_cm)
    API->>API: level dari pipe zero → protocol.stage_on(day)
    API->>W: prakiraan hujan 72 jam
    API->>API: scheduler.decide(level, stage, rain72 BMKG) ; LogReg HITL hanya flag UI
    API->>DB: reading + decision (+ irrigation) + receipt IPCC Tier-1
    U->>NX: buka dashboard, unggah foto daun, chat asisten
    NX->>API: rewrite /api/* → :8000
    API->>V: image guard → inferensi ONNX CPU (jalur live yang sama untuk foto juri)
    V-->>API: kelas penyakit + severity + advisory ID/EN
    API->>API: fusion risk = penyakit × awd_state × wet_weather (rain72 ≥ 15 mm)
    API->>DB: vision_report
    API->>L: assistant/chat - tool-calling ≤6 hop, timeout 30 s
    L-->>API: jawaban via 6 tools (status, cuaca, triage, kb, receipt, risiko)
    API-->>U: JSON via Next.js (online) atau fallback TF-IDF (badge offline)
```

## Poin penting

- **Decision-at-ingest**: keputusan dihitung saat `POST /api/ingest` dan disimpan
  ke tabel `decisions`; dashboard dan asisten hanya membaca - tidak ada logika
  irigasi yang terduplikasi di luar `apps/api/app/irrigation/`.
- **Scaled ÷3**: petak `scaled=true` (mesokosmos) dikonversi sebelum `decide`
  sehingga pemicu negatif lapangan −15 cm setara −5 cm bak; **hanya pemicu
  negatif yang diskalakan** - target genang establishment/flowering_lock tetap
  unscaled (rasio ÷3 dijelaskan di `docs/METHODOLOGY.md`).
- **Kontrak demo/juri**: `POST /api/demo/seed` menghasilkan plot demo deterministik
  (`is_demo=1`, badge DEMO di UI); foto dari juri diproses lewat **jalur ONNX live
  yang identik** dengan produksi - tidak ada jalur mock terpisah.
- **Honesty labels**: receipt karbon selalu membawa salah satu label
  `simulated | measured | projected`; angka eksperimen dilaporkan sebagai
  `[simulated]` sampai tervalidasi lapangan. Angka literatur (Carrijo,
  Lampayan, Zhao) adalah agregat lapangan terpisah, bukan petak demo.
- **Rain HITL**: LogReg persistensi tidak boleh men-skip irigasi; muka air
  ≥ 0 cm tidak boleh DRAIN di luar panen.
- **Offline ladder**: LLM online (DeepSeek, tool-calling ≤6 hop, 30 s) → jika
  gagal/tidak ada kunci API → fallback retrieval TF-IDF atas `apps/api/app/kb/*.md`
  plus one-liner status petak, ditandai badge mode offline di UI.

## Roadmap integrasi pesan

Desain IRIS bersifat **transport-agnostic**: seluruh isi komunikasi petani dibangun
oleh builder murni (teks status, rekomendasi, receipt, jawaban KB) yang tidak
mengenal library transport mana pun. Hari ini kanal utamanya adalah web
(Next.js + REST). Adapter pesan instan berikutnya yang direncanakan adalah
**WhatsApp Business API** - cukup menambahkan adapter baru yang memetakan pesan
masuk ke endpoint API yang sama, tanpa mengubah logika irigasi, vision, maupun
asisten.

## Indeks dokumentasi

- `docs/METHODOLOGY.md` - metode AWD, scaling mesokosmos, metrik air
- `docs/IPCC_ACCOUNTING.md` - detail akuntansi CH4/CO2e Tier-1
- `docs/SENSOR_VALIDATION.md` - prosedur validasi sensor
- `docs/DEPLOYMENT_GUIDE.md` - panduan deployment
- `docs/poster-content.md` - konten poster
- `docs/MODEL_CARD.md` - kartu model visi
- `experiments/DEFINISI_METRIK.md` - definisi metrik eksperimen
- `docs/history/` - arsip
