# Definisi Metrik Pengujian IRIS

| Eksperimen | Metrik | Jenis |
| --- | --- | --- |
| E1 - Akurasi sensor level | MAE, RMSE (cm) antara pembacaan sensor dan pengukuran manual | measured |
| E2 - Prototipe fisik AWD | Total volume air (mL), persen waktu aerated (% hari dengan level < 0 cm) | measured |
| E3 - Backtest simulasi | water_saved_pct (%), rule conformance (irigasi hanya saat level <= trigger), CH4 dan CO2e saved | simulated |
| E4 - Evaluasi model AI-Vision | macro-F1 held-out, akurasi per kelas, confusion matrix (dataset publik; validasi lapangan menyusul) | public-dataset |

## Catatan asumsi E3 (backtest)

- Jalur CF memakai drawdown konstan; jalur AWD memakai drawdown penuh saat
  muka air >= 0 cm dan drawdown setengah (0,5x) saat aerated (level < 0 cm)
  sebagai proksi menurunnya ET/kapilaritas saat tanah mengering.
- Kedua jalur di-cap pada REFILL_CM + 10 cm agar hujan berlebih tidak
  menumpuk tanpa batas.
- water_saved_pct memakai zero-guard: bernilai 100,0 jika baseline CF tidak
  mengirigasi sama sekali (mis. hujan terus-menerus sepanjang musim).
- Emisi CH4 memakai IPCC Tier-1: SF_W efektif dari fraksi hari genang (AWD)
  vs 1,0 (CF), GWP100 CH4 non-fosil = 27.
- Backtest tidak memakai HOLD_FOR_RAIN; kebijakan rain-hold scheduler live
  didokumentasikan kanonik di `docs/METHODOLOGY.md` (bagian kebijakan
  rain-hold scheduler), termasuk **Do not drain** (hujan lama tidak
  mengeringkan paksa) dan LogReg HITL yang tidak mengubah `rain72`.
- Klaim E3 dilabeli `[simulated]`. Angka literatur (Carrijo/Lampayan/Zhao)
  adalah agregat lapangan terpisah; jangan dicampur ke baris E3.
