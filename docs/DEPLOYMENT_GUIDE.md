# Panduan Deployment IRIS

Platform IRIS berjalan sebagai **dua layanan**:

| Layanan | Port | Lokasi | Cara jalan |
| --- | --- | --- | --- |
| Backend API (FastAPI) | `:8000` | `apps/api` | venv di root repo `.venv`, dijalankan via uvicorn |
| Frontend (Next.js) | `:3000` | `apps/web` | produksi: `npm run build` + `npm run start`; dev: `npm run dev` |

Database memakai SQLite di `apps/api/storage/iris.db` - **dibuat otomatis
saat backend pertama kali boot**; tidak perlu setup database manual.

## Prasyarat

- **Python 3.11+** - cek dengan `python --version`
- **Node.js 18+ dan npm** - cek dengan `node -v` dan `npm -v`
- **Git**
- `DEEPSEEK_API_KEY` (opsional - tanpa key, asisten tetap jalan dalam mode offline, lihat bagian [Mode Offline](#mode-offline))

## Setup Lokal

> Catatan PowerShell 5.1: gunakan `;` untuk merangkai perintah, bukan `&&`.

### Windows PowerShell

```powershell
git clone <URL_REPO>
cd iris-platform

# 1. Virtualenv + dependensi backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r apps\api\requirements.txt

# 2. Dependensi frontend
cd apps\web
npm install

# 3. Seed data demo (idempoten)
cd ..\api
..\..\.venv\Scripts\python.exe scripts\seed_demo.py

# 4. Jalankan backend
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

Frontend dijalankan di terminal baru (lihat bagian [Menjalankan](#menjalankan)).

### Linux / macOS (bash)

```bash
git clone <URL_REPO>
cd iris-platform

# 1. Virtualenv + dependensi backend
python3 -m venv .venv
.venv/bin/python -m pip install -r apps/api/requirements.txt

# 2. Dependensi frontend
cd apps/web
npm install

# 3. Seed data demo (idempoten)
cd ../api
../../.venv/bin/python scripts/seed_demo.py

# 4. Jalankan backend
../../.venv/bin/python -m uvicorn app.main:app --port 8000
```

## Variabel Lingkungan

| Variabel | Default | Wajib? | Keterangan |
| --- | --- | --- | --- |
| `DEEPSEEK_API_KEY` | kosong | Tidak | Kunci API LLM. Jika kosong → asisten berjalan **mode offline** dengan badge di UI |
| `IRIS_LLM_MODEL` | `deepseek-v4-flash-vision-exp` | Tidak | ID model DeepSeek (vision-exp, 21 Agustus 2026) |
| `IRIS_DB` | anchor absolut ke `apps/api/storage/iris.db` | Tidak | Lokasi database SQLite. Default tidak bergantung direktori kerja proses |
| `IRIS_DEVICE_TOKEN` | kosong (tidak aktif) | Tidak | Jika diset, `POST /api/ingest` wajib menyertakan header `X-IRIS-Token` (divalidasi constant-time compare) |
| `WEB_ORIGIN` | kosong | Tidak | Origin frontend untuk CORS |
| `BMKG_ADM4` | `33.73.01.1003` | Tidak | Kode wilayah tingkat IV (kelurahan/desa) untuk prakiraan BMKG. Default: Kelurahan Salatiga, Kec. Sidorejo |
| `BMKG_API_KEY` | kosong | Tidak | Opsional. Endpoint publik BMKG tidak mewajibkan kunci |

LogReg HITL hujan (`rain_hitl.py`) memanggil Open-Meteo untuk hujan 1/3 hari
terakhir. Jika panggilan gagal, flag HITL tetap jalan dengan fitur hari-dalam-tahun
saja (`doy_only`) dan **tidak** mengubah `rain72` BMKG.

Contoh set variabel di PowerShell (terminal yang sama dengan tempat backend
dijalankan):

```powershell
$env:DEEPSEEK_API_KEY = "sk-..."
$env:IRIS_DEVICE_TOKEN = "token-perangkat-yang-kuat"
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

## Menjalankan

### Backend (terminal 1)

Dari folder `apps/api`:

```powershell
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

### Frontend produksi (terminal baru)

```powershell
cd apps\web
npm run build
npm run start
```

Buka http://localhost:3000.

### Mode development frontend

Untuk pengembangan dengan hot reload, ganti dua perintah di atas dengan:

```powershell
npm run dev
```

## Health Check

Cek kondisi layanan lewat endpoint:

```
GET /api/health
```

Respons berisi `{status, db, onnx, llm, mode}`:

- `db` - status koneksi SQLite.
- `onnx` - apakah model ONNX berhasil dimuat.
- `llm` - apakah LLM dapat dijangkau.
- `mode` - `live` ketika **onnx termuat**, **llm reachable**, dan sistem siap.

Uji cepat dari PowerShell:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

## Mode Offline

IRIS punya tangga degradasi (offline ladder):

1. Saat LLM gagal dijangkau, sistem **melakukan retry** beberapa kali.
2. Bila tetap gagal, fallback ke mesin berbasis **TF-IDF**.
3. UI menampilkan **badge offline** agar pengguna tahu jawaban berasal dari
   mode lokal, bukan LLM.

Artinya demo tidak akan mati total karena jaringan/API key bermasalah  - 
asisten tetap menjawab dalam mode offline.

## Catatan Demo / Panggung

- Jalankan `scripts/seed_demo.py` sebelum demo untuk mengembalikan data contoh;
  seeding **aman dijalankan ulang (idempoten)** sehingga tidak menduplikasi data.
- Set `DEEPSEEK_API_KEY` di terminal tempat backend diluncurkan agar mode live;
  jika lupa, badge offline muncul - masih aman untuk dipentaskan.

## Pembaruan

Saat menarik perubahan terbaru dari repo:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -r apps\api\requirements.txt   # jika requirements berubah
cd apps\web ; npm install ; npm run build   # rebuild wajib untuk frontend
cd ..\api
..\..\.venv\Scripts\python.exe scripts\seed_demo.py   # reseed aman (idempoten)
```

Setelah itu jalankan ulang backend dan frontend (`npm run start`).

## Troubleshooting

| Gejala | Penyebab | Solusi |
| --- | --- | --- |
| Port 8000 sudah terpakai | Proses lain memegang port | Cari PID: ``netstat -ano \| findstr :8000`` lalu hentikan: `taskkill /PID <pid>` |
| Health menunjukkan `llm` unreachable | Key belum diset di terminal yang sama dengan backend, atau key invalid | Set `$env:DEEPSEEK_API_KEY` lalu jalankan ulang backend; sistem tetap jalan di mode offline |
| Boot backend terasa lambat | ONNX model dimuat saat startup | Perilaku normal - tunggu sampai `/api/health` sehat sebelum membuka aplikasi |
| Upload foto ditolak `422 image_rejected` / `low_confidence` | Foto tidak lolos validasi kualitas/kemiripan | Ini **perilaku yang benar** - ambil ulang foto sesuai panduan (fokus, pencahayaan cukup) |
| Build Next.js gagal | Cache build korup | Hapus folder `apps/web/.next` lalu `npm run build` ulang |

## Keamanan

- **Jangan commit `DEEPSEEK_API_KEY`** ke repository - set hanya lewat
  environment variable terminal, bukan file yang ikut ter-commit.
- **Rotasi API key sebelum repo dipublikasikan**, karena riwayat git bisa
  membocorkan key yang pernah tersimpan.
- Untuk ingest di lingkungan produksi, **set `IRIS_DEVICE_TOKEN`** agar
  `POST /api/ingest` mewajibkan header `X-IRIS-Token`.
