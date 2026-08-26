# Metodologi Pengujian IRIS (E1–E4)

Ringkasan metrik juga tersedia di `experiments/DEFINISI_METRIK.md`. Label sumber
data mengikuti green receipts: `measured` (data lapangan nyata),
`simulated` (model/backtest), `projected` (proyeksi ke musim/lahan lain).

## E1 - Akurasi sensor level air (`measured`)

- **Pertanyaan:** seberapa akurat node ultrasonik pada pipa AWD dibanding
  pengukuran manual?
- **Metrik:** MAE dan RMSE dalam cm antara `node_cm` dan `manual_cm`.
- **Protokol:**
  1. Kalibrasi `pipe_zero_cm` = jarak sensor ke permukaan air saat level 0 cm
      (datum tanah) - bukan saat genangan +5 cm; saat genangan +5 cm,
      `dist_cm` = `pipe_zero_cm` − 5 (API menghitung `level_cm = pipe_zero_cm −
      dist_cm`, sehingga anchor di permukaan +5 cm akan menggeser semua level
      −5 cm). Detail di `docs/SENSOR_VALIDATION.md`.
  2. Ambil ≥30 pasangan bacaan simultan manual vs node yang mencakup rentang
     level +15 cm sampai −20 cm (genang penuh hingga drawdown AWD).
  3. Catat tiap pasangan pada CSV `manual_cm,node_cm,ts`
     (format lengkap di `docs/SENSOR_VALIDATION.md`).
  4. Hitung `MAE = mean(|node − manual|)` dan
     `RMSE = sqrt(mean((node − manual)^2))`.
- **Target diterima (usulan):** MAE ≤ 2 cm - cukup untuk selisih pemicu 15 cm;
  finalisasi target bersama pembimbing.
- **Output:** tabel MAE/RMSE per node di `experiments/outputs/`, label `measured`.

## E2 - Prototipe fisik safe-AWD skala mesokosmos (`measured`)

- **Pertanyaan:** apakah aturan safe-AWD dengan pemicu terskala hemat air pada
  implementasi fisik (ember/mesokosmos) tanpa menstres tanaman?
- **Setup:** dua unit identik - kontrol continuous flooding (CF) vs safe-AWD
  dengan `scaled=True` (pemicu −5 cm). Sensor sama dengan E1.
- **Metrik:** total volume air irigasi (mL, ditakar/gelas ukur) dan persen hari
  aerated (hari dengan level < 0 cm).
- **Protokol:** jalankan satu siklus vegetatif penuh; isi hingga +5 cm saat
  pemicu tercapai (AWD) atau jaga genangan (CF); catat setiap penambahan air.
- **Analisis:** bandingkan volume total dan % hari aerated AWD vs CF;
  label `measured`.

### Rasional pemicu terskala (−15 cm → −5 cm, ÷3)

Di lapangan, safe-AWD standar mengairi kembali saat muka air turun 15 cm di
bawah permukaan (`trigger_level_cm` = −15.0 pada `veg_awd` dan
`grain_fill_awd`). Wadah mesokosmos hanya sedalam ±15–20 cm kolom air, sehingga
drawdown −15 cm mustahil dicapai tanpa mengeringkan akar. Kedalaman kolom air
perwakilan lapangan : wadah ≈ 3 : 1, maka pemicu lapangan dibagi tiga menjadi
**−5 cm** (`trigger_level_cm(stage, scaled=True)` membagi semua pemicu negatif
dengan 3). Konsistensi logika dijaga dari dua arah:

- API (`POST /api/ingest`) melipatgandakan level terukur ×3 sebelum
  `decide()` untuk petak `scaled=true`, sehingga aturan identik skala lapangan
  (negative-trigger stages only; establishment/flowering flood targets stay
  unscaled).
- Backtest E3 memakai pemicu ÷3 langsung ketika flag `--scaled` aktif.

Rasio ini adalah asumsi proyek (bukan nilai IPCC); dokumentasikan kedalaman
wadah aktual saat pelaporan.

## E3 - Backtest simulasi AWD vs CF (`simulated`)

- **Alat:** `apps/api/app/backtest/engine.py`, driver
  `apps/api/scripts/backtest.py`, orkestrator `experiments/run_all.py`.
- **Parameter default:** 100 hari, drawdown 0.8 cm/hari, hujan 0 mm,
  luas 1 ha, tanpa skala. Jalur AWD memakai pemicu per fase
  (`stage_on` + `trigger_level_cm`), refill ke +5 cm.
- **Asumsi model** (juga di `experiments/DEFINISI_METRIK.md`):
  drawdown aerated dihalvingkan (0.5× saat level < 0 cm) sebagai proksi
  menurunnya ET/kapilaritas; level dicap pada REFILL_CM+10 cm;
  zero-guard water_saved_pct = 100 % bila CF tidak mengirigasi;
  emisi Tier-1 dengan SF_w_eff dari fraksi hari genang.
  Tambahan penelusuran angka:
  - Jumlah irigasi CF sama dengan jumlah hari murni karena CF dimodelkan
    sebagai top-up harian defisit 0.8 cm pada hujan nol - artefak dosing
    harian; VOLUME justru digerakkan asumsi laju drawdown, bukan hitungan
    event.
  - Backtest memakai aturan pemicu polos dan tidak pernah memakai
    HOLD_FOR_RAIN: hujan prakiraan dikreditkan penuh pada hari yang sama.
  - Volume per event = `deficit_cm × 100 × area_ha` m³
    (`level_cm_to_m3`) - menelusuri 8 000 m³ CF (0.8 cm/hari × 100 hari ×
    1 ha) dan 5 000 m³ AWD.
- **Metrik:** `water_saved_pct`, conformance aturan (irigasi hanya saat
  level ≤ pemicu), CH4 dan CO₂e saved.
- **Perintah regenerasi:** dari root repo `python experiments/run_all.py`
  (menjalankan backtest dan menulis ulang
  `experiments/outputs/backtest_summary.json`);
  variasi via flag `--days --drawdown --rain-mm --area-ha --scaled`.
- **Hasil saat ini** (komit `backtest_summary.json`, label `simulated`):
  lihat tabel pada README bagian *Hasil Ringkas* - 23 vs 100 irigasi,
  5 000 vs 8 000 m³ air, sf_w_eff 0.8922, 0.3784 t CO₂e/ha/musim terhindar,
  penghematan air 37.5 %. Label **This prototype [simulated]**. Agregat
  literatur (bukan petak ini): air mild AWD −23,4% (Carrijo 2017), adopsi
  hingga −38% (Lampayan 2015); CH4 mild AWD −49,4% / overall −51,6%
  (Zhao 2024). Jangan mencampur kedua label.

### Kebijakan rain-hold scheduler live (`apps/api/app/irrigation/scheduler.py`)

Berlaku pada sistem live (bukan bagian backtest E3 - lihat asumsi di atas):

- Prakiraan hujan ≥ `RAIN_SKIP_MM` = **15 mm dalam 72 jam** menahan irigasi
  (`HOLD_FOR_RAIN`);
- penahanan hanya berlaku selama level masih di atas **pemicu − 10 cm**
  (`hard_floor`); bila level sudah menyentuh floor, irigasi tetap dieksekusi;
- fase `establishment` dan `flowering_lock` **dikecualikan** dari rain-hold
  (genangan fase kritis selalu dipertahankan);
- **Do not drain (pita AWD dangkal):** jika muka air sudah ≥ 0 cm dan
  masih di atas pemicu, tetapi **< 15 cm** (bukan panen), aksi = `WAIT`
  dengan alasan "Do not drain". Hujan yang menjaga genangan dangkal
  (daun di udara) tidak memicu pengeringan paksa ke −15 cm;
- **LOWER_POND (genangan berlebih):** jika muka air ≥ **15 cm**, aksi =
  `LOWER_POND`: turunkan ke arah +5 cm *jika* ada saluran/pintu/overt
  pematang, agar kanopi tetap di udara. Ini relief banjir, bukan AWD.
  `DRAIN` sampai kering hanya pada `harvest`. Evaporasi saja terlalu
  lambat pada kedalaman itu.
- **LogReg HITL** (`rain_hitl.py`): opini kedua vs BMKG. Tidak mengubah
  `rain72` scheduler. Flag tinjauan manusia jika prediksi basah/kering
  berbeda atau P(wet) di pita 0,35–0,65. Bobot di `rain_logreg.json`
  (Open-Meteo Salatiga; akurasi latih ~0,59, base rate ~0,50). Bukan
  pengganti BMKG dan bukan pengukur lapangan.

Deviasi flowering-lock vs panduan IRRI RKB: pemicu +3 cm dengan refill ke
+5 cm menjaga pita ±3–5 cm, sedikit lebih longgar dari panduan IRRI RKB
("keep ~5 cm" sejak heading); dipilih agar konservatif terhadap stres pada
fase kritis namun tetap praktis.

## E4 - Evaluasi model AI-Vision (`public-dataset`)

- **Pertanyaan:** seberapa andal klasifikasi 5 kelas daun padi (blast, bercak
  cokelat, tungro, hawar daun bakteri, sehat) pada model ONNX yang dipakai
  produksi?
- **Metrik:** macro-F1, akurasi per kelas, dan confusion matrix pada
  *held-out test split*; dilaporkan bersama keterbatasan data.
- **Status:** v0.3 dilatih di RTX 3060 pada Mendeley yang di-deduplikasi MD5
  plus foto lapangan Paddy Doctor (`[public-dataset]`). Tes held-out: akurasi
  0,9784, macro-F1 0,9783 (1.621 citra). Skor validasi 1,00 pada v0.2 dicatat
  sebagai kebocoran split, bukan patokan. Validasi lapangan dengan daun
  Indonesia menyusul bersama mitra agronomi.
- **Protokol evaluasi:** unik per MD5 sebelum split 70/15/15; preprocess
  latihan = serving (`Resize` sisi pendek 256 + `CenterCrop` 224); laporan di
  `docs/MODEL_CARD.md`; guard kualitas gambar diuji terpisah pada suite
  `apps/api/tests`.
- **Output:** tabel metrik + model card di `docs/MODEL_CARD.md`,
  label `public-dataset` sampai validasi lapangan tersedia.
