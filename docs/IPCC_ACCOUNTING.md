# Akuntansi Karbon IRIS - IPCC Tier-1

Implementasi: `apps/api/app/irrigation/ipcc.py`. Semua angka emisi pada green receipt
IRIS dihitung dengan persamaan Tier-1 IPCC 2006 Guidelines (Vol. 4, Ch. 5  - 
Cultivated Rice) dikombinasikan dengan GWP100 CH4 dari AR6.

## Persamaan

Struktur resmi (IPCC 2006 Guidelines Vol.4 Ch.5): emisi musiman memakai EF_c
yang sudah memuat seluruh faktor skala - tidak ada faktor skala ganda di dalam
persamaan musiman.

1. Emisi CH4 musiman (Tier-1):

   ```
   CH4 = EF_c × t × A
   ```

   dengan `t` = panjang musim (hari), `A` = luas (ha); untuk inventori nasional
   hasil dikonversi ke Gg dengan pengali 10^-6. Di kode:
   `seasonal_ch4_kg(t_days, area_ha, sf_w, sf_p, sf_o)`.

2. Faktor emisi harian EF_c (bentuk Eq. 5.2):

   ```
   EF_c = EF_base × SF_w × SF_p × SF_o   (kg CH4/ha/hari)
   ```

   `EF_base` default 1.30 kg CH4/ha/hari dari Table 5.11; suku tanah `SF_s,r`
   ada dalam GL tetapi dikecualikan secara default. Nilai SF_w diambil dari
   Table 5.12 (irrigated–continuously flooded = 1; multiple aeration = 0.78).

3. SF_w efektif IRIS (interpolasi linear proyek, bukan rumus resmi IPCC  - 
   lihat checklist):

   ```
   SF_w_eff = 1.0 − (1.0 − 0.78) × (1 − flooded_days / season_days)
   ```

   yaitu interpolasi antara SF_w genangan kontinu (1.00) dan SF_w multiple
   aeration (0.78) menurut fraksi hari tergenang. Contoh E3: 51/100 hari
   tergenang → SF_w_eff = 0.8922. Justifikasi: SF_w_eff adalah interpolasi
   linear antara dua faktor terdekat IPCC 2006 Table 5.12 (continuously
   flooded 1,00; multiple aeration 0,78 [0,62–0,98]) berdasarkan fraksi hari
   tergenang, menghasilkan faktor tertimbang-musim untuk rezim AWD di antara
   kedua kategori; ini mempertahankan ujung konservatif tanpa diskontinuitas
   antar-kategori diskrit IPCC.

4. Konversi ke CO₂e:

   ```
   CO2e (ton) = CH4_saved (kg) × 27 / 1000
   ```

5. Green receipt (`build_receipt`): baseline memakai SF_w = 1.00 (continuous
   flooding), skenario IRIS memakai SF_w_eff; penghematan = baseline − aktual.
   Receipt menolak baseline air ≤ air aktual (zero-savings guard) dan
   memerlukan `season_days > 0`.

## Tabel konstanta

| Konstanta | Nilai kode | Sumber yang diklaim | Status |
| --- | --- | --- | --- |
| `EF_BASE_KG_CH4_HA_DAY` | 1.3 kg CH4/ha/hari | Table 5.11, baris continuously flooded tanpa amendemen organik (rentang error 0.80–2.20; Yan et al. 2005) | **[VERIFIED 2006GLs Vol.4 Ch.5 Tables 5.11 & 5.12]** |
| `SF_W_CONTINUOUS` | 1.0 | Table 5.12, baris irrigated–continuously flooded (kasus agregat) | **[VERIFIED 2006GLs Vol.4 Ch.5 Tables 5.11 & 5.12]** |
| `SF_W_MULTIPLE_AERATION` | 0.78 | Table 5.12, baris irrigated–multiple aeration (rentang error 0.62–0.98) | **[VERIFIED 2006GLs Vol.4 Ch.5 Tables 5.11 & 5.12]** |
| `SF_p` (pra-musim) | 1.0 (default) | Table 5.12, baris pre-season non-flooded <180 hari | **[VERIFY]** |
| `SF_o` (amendemen) | 1.0 (default) | Table 5.12, baris amendemen organik = tidak ada | **[VERIFY]** |
| `GWP100_CH4_AR6` | 27 (CH4 non-fosil) | IPCC AR6 WG1 Ch.7 §7.6.1.5, Tables 7.15 & 7.SM.7 (27.0 ± 11) | **[VERIFIED AR6 WGI Ch.7]** |
| Interpolasi SF_w_eff | linear pada fraksi hari genang | Asumsi proyek IRIS (bukan IPCC) | Tinjauan reviewer |

## Delta 2019 Refinement (IPCC 2019 Refinement to the 2006 Guidelines, Vol. 4)

Sumber: https://www.ipcc-nggip.iges.or.jp/public/2019rf/pdf/4_Volume4/19R_V4_Ch05_Cropland.pdf
(diakses 2026-08-25).

IRIS tetap memakai basis 2006 GLs untuk angka yang sudah terverifikasi di atas,
tetapi dokumen ini mencatat secara eksplisit apa yang berubah pada **IPCC 2019
Refinement** agar arah bias diketahui:

- **EF_c regional (Indonesia - kawasan Asia Tenggara) diperbarui menjadi
  1.22 kg CH4/ha/hari** (rentang ketidakpastian 95 %: 0.83–1.81), menggantikan
  default global 1.30 (2006 GLs, Table 5.11).
- **Durasi kultivasi default `t` = 102 hari** (rentang 78–150 hari). Nilai ini
  mendukung pemakaian `t = 100` hari pada receipt IRIS.
- **Tabel 5.12 versi 2019** untuk sawah irigasi: kasus agregat SF_w = 0.60;
  disagregasi - continuously flooded 1.00 (tidak berubah), single drainage
  0.71, multiple drainage termasuk AWD **0.55** (rentang 0.41–0.72).
- **Bab 11 (N2O dari lahan terkelola):** faktor emisi EF1FR baru untuk sawah  - 
  genangan kontinu 0.003 vs drainase termasuk AWD 0.005 kg N2O-N/kg N.

Konsekuensi kejujuran akuntansi:

1. SF_w = 0.78 (basis 2006) **meremehkan (understates) manfaat CH4** dibanding
   nilai 2019 (multiple aeration/AWD 0.55). Arah bias ini konservatif: klaim
   penghematan IRIS tidak melebih-lebihkan.
2. Receipt hanya menghitung CH4; penalti N2O dari drainase (EF1FR 0.005 vs
   0.003) belum dinetralkan, sehingga angka CO2e adalah **batas atas**
   (upper bound) manfaat iklim bersih.

## Checklist verifikasi vs IPCC 2006 Vol.4 Ch.5 Table 5.12

Lakukan sebelum klaim publikasi/kompetisi; centang dengan nomor halaman/tabel
resmi sebagai bukti:

- [x] V1 - EF_c default 1.30 kg CH4/ha/hari untuk sawah irigasi tergenang
      kontinu tanpa amendemen organik sesuai Table 5.11 (kolom default EF;
      rentang error 0.80–2.20, Yan et al. 2005).
- [x] V2 - SF_w continuously flooded = 1.00 sesuai Table 5.12 (kasus agregat).
- [x] V3 - SF_w multiple aeration = 0.78 sesuai Table 5.12 (interval
      ketidakpastian 95 % dicatat: 0.62–0.98).
- [ ] V4 - SF_p = 1.0 sesuai baris pre-season yang dipakai (non-flooded <180
      hari sebelum musim tanam).
- [ ] V5 - SF_o = 1.0 sesuai baris amendemen (tanpa input organik).
- [x] V6 - Konfirmasi GWP100 CH4 non-fosil = 27 dari AR6 Table 7.SM.7;
      **TERVERIFIKASI: 27.0 ± 11 (AR6 WGI Ch.7 §7.6.1.5, Tables 7.15 &
      7.SM.7; https://www.ipcc.ch/report/ar6/wg1/downloads/report/IPCC_AR6_WGI_Chapter07.pdf)**;
      putuskan apakah skema pelaporan target mensyaratkan GWP lain
      (SAR = 21, AR5 = 28) - 2006 Guidelines sendiri tidak mengikat GWP.
- [ ] V7 - Konfirmasi durasi musim `t = 100 hari` wajar untuk varietas lokal
      (parameter `season_days`, bukan konstanta IPCC).
- [ ] V8 - Catat bahwa SF_w_eff adalah interpolasi linear proyek antara dua
      baris Table 5.12; minta persetujuan pembimbing/reviewer.
- [ ] V9 - Label green receipt: rilis saat ini selalu memancarkan `simulated`;
      `measured` akan dipasang begitu data pilot bench/lapangan masuk;
      `projected` dicadangkan untuk proyeksi skala nasional.

## Reproduksi

Dari `apps/api/` (venv repo di `.venv`):

```python
from app.irrigation.ipcc import build_receipt
r = build_receipt("Sawah Uji", season_days=100, flooded_days=51,
                  water_baseline_m3=8000.0, water_actual_m3=5000.0,
                  label="simulated")
print(r.ch4_saved_kg, r.co2e_saved_t)  # 14.01  0.3784
```

Regenerasi angka E3 lengkap: dari root repo `python experiments/run_all.py`
(menulis `experiments/outputs/backtest_summary.json`).

Catatan pembulatan: CO₂e dihitung dari selisih CH₄ tak-dibulatkan (14.014 kg);
hitung-ulang dari angka tampil 14.01 kg menghasilkan 0.3783 t.

Tes terkait: `apps/api/tests/test_ipcc.py`, `apps/api/tests/test_receipts.py`,
`apps/api/tests/test_backtest.py` (pin angka E3).
