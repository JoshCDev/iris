# Protokol Validasi Sensor Level IRIS

Template eksperimen E1 (`docs/METHODOLOGY.md`) - akurasi node ultrasonik pada
pipa AWD vs pengukuran manual. Hasil berlabel `measured`.

## Alat

- Node ultrasonik terpasang di pipa AWD berlubang (firmware kirim
  `dist_cm` ke `POST /api/ingest`, header `X-IRIS-Token`).
- Meteran ukur/penggaris untuk pembacaan manual.
- Perangkat pencatat waktu (jam yang sama untuk semua petugas).

## Sensor physics caveats (JSN-SR04T)

- **Blind zone ≈ 25 cm.** Pada genangan acuan +5 cm di pipa setinggi 30 cm,
  permukaan air berada tepat di batas jarak minimum sensor - geometri pemasangan
  wajib menjaga jarak sensor→air > 25 cm atau gunakan pipa lebih tinggi.
- **Lebar beam 45–75°.** Beam lebar memantul pada dinding pipa sempit
  (multi-echo) dan dapat menghasilkan pembacaan palsu; pertimbangkan pipa
  berdiameter lebih besar atau baffle.
- **Drift kecepatan suara ≈ 1 cm per 15 °C** tanpa kompensasi suhu; catat suhu
  saat kalibrasi atau tambahkan kompensasi di firmware.

Target akurasi: MAE diterima **≤ 2 cm** (investigasi residual > 5 cm) - target
lama ≤ 0.5 cm tidak realistis untuk sensor ini dan dicabut.

## Persiapan & kalibrasi

1. Pastikan pipa AWD vertikal, lubang bersih, dasar pipa menembus zona akar.
2. Tetapkan `pipe_zero_cm` = jarak sensor ke permukaan air saat level 0 cm
   (datum tanah) - bukan saat genangan +5 cm; saat genangan +5 cm,
   `dist_cm` = `pipe_zero_cm` − 5; kirim pada bacaan pertama via field opsional
   `pipe_zero_cm` di `POST /api/ingest` (plot dibuat otomatis pada bacaan
   pertama dengan `device_plot_name` yang sama; tanpa field ini default 30 cm).
3. Level dihitung API sebagai `level_cm = pipe_zero_cm − dist_cm`; pembacaan
   manual harus dikonversi ke konvensi yang sama (0 cm = permukaan tanah,
   positif = genangan).

## Prosedur pengambilan data

1. Untuk tiap titik sampel: baca manual dan node dalam interval < 60 detik
   (air relatif statis; hindari saat hujan/angin kencang).
2. Cakup ≥30 pasangan yang merata pada rentang +15 cm … −20 cm:
   genangan penuh, penurunan bertahap, titik pemicu −15 cm, dan sedikit di
   bawahnya. Tambahkan 3 pasang ulang di satu titik untuk cek repeatability.
3. Catat kondisi ekstra bila ada: `batt_v`, `rssi` (opsional, kolom tambahan
   di kanan), cuaca, petugas.
4. Simpan berkas sebagai `experiments/data/sensor_validation_<node>.csv`.

## Format CSV

Header persis (urutan kolom wajib):

```csv
manual_cm,node_cm,ts
```

Contoh isi:

```csv
manual_cm,node_cm,ts
5.1,5.3,2026-08-22T08:00:00+07:00
2.0,2.4,2026-08-22T09:00:00+07:00
-5.2,-4.7,2026-08-22T10:00:00+07:00
-15.1,-14.2,2026-08-22T11:00:00+07:00
```

Ketentuan kolom:

| Kolom | Unit | Konvensi |
| --- | --- | --- |
| `manual_cm` | cm | level manual (0 = permukaan tanah, positif = genangan) |
| `node_cm` | cm | level node = `pipe_zero_cm − dist_cm` |
| `ts` | ISO-8601 | waktu bacaan, sertakan offset zona (mis. +07:00) |

## Analisis

```python
import pandas as pd
df = pd.read_csv("experiments/data/sensor_validation_<node>.csv")
err = df.node_cm - df.manual_cm
mae = err.abs().mean()
rmse = (err ** 2).mean() ** 0.5
print(mae, rmse)
```

- Lapikan MAE/RMSE per node; target diterima usulan MAE ≤ 2 cm
  (lihat blok *Sensor physics caveats*; finalisasi bersama pembimbing).
- Investigasi residual > 5 cm (kemungkinan: `pipe_zero_cm` bergeser,
  multi-echo ultrasonik, riak).
- Repeatability: simpangan baku 3 pasang ulang ≤ 0.5 cm.

## Tindak lanjut

- Nilai MAE/RMSE masuk tabel E1 di `experiments/outputs/` dengan label
  `measured`.
- Bila MAE > target: perbaiki pemasangan/aliasing sensor, ulangi protokol;
  jangan lanjut ke E2 sebelum lolos.
