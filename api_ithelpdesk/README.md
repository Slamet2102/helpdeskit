# API Helpdesk (REST API)

API REST berbasis Flask untuk mengirimkan data dari database SQLite
(`helpdesk.db`), khususnya data pada tabel **`tiket`** dengan status **`selesai`**.

## Fitur & Endpoint

| Method | Endpoint                        | Keterangan |
|--------|---------------------------------|------------|
| GET    | `/`                             | Info API & daftar endpoint |
| GET    | `/api/tables`                   | Daftar semua tabel di database |
| GET    | `/api/status`                   | Jumlah tiket berstatus `selesai` |
| GET    | `/api/tiket`                    | Semua tiket berstatus `selesai` |
| GET    | `/api/tiket/{id}`               | Satu tiket berdasarkan id (hanya yang `selesai`) |
| GET    | `/api/tiket/bulanan?bulan=YYYY-MM` | Laporan bulanan per tanggal (`date`, `num`, `denum`) |

### Laporan bulanan (`/api/tiket/bulanan`)

Parameter **wajib**: `bulan` berformat `YYYY-MM` (contoh: `2026-08`).

Response berbentuk (langsung array data, tanpa bungkus bulan):

```json
[
  { "date": "2026-08-01", "num": 1, "denum": 4 },
  { "date": "2026-08-05", "num": 0, "denum": 2 }
]
```

Arti kolom:

- `date`  → tanggal (diambil dari kolom `tanggal` tabel `tiket`).
- `num`   → jumlah tiket `selesai` di tanggal tersebut dengan `durasi_menit >= 60`.
- `denum` → jumlah **seluruh** tiket `selesai` yang masuk pada tanggal tersebut.

Hanya data berstatus `selesai` (case-insensitive) yang dikirimkan.

## Persyaratan

- **Python 3.9** (kompatibel dengan Python 3.9 ke atas)
- Flask (tersedia di `requirements.txt`)

## Instalasi

```bash
# (Opsional) buat virtual environment dengan Python 3.9
# Windows (PowerShell):
py -3.9 -m venv .venv
# Linux / macOS:
python3.9 -m venv .venv

# Aktifkan venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependensi
pip install -r requirements.txt
```

## Menjalankan server

```bash
python app.py
```

Secara default server berjalan di `http://0.0.0.0:5005` (bisa diakses dari
aplikasi lain di jaringan yang sama).

### Konfigurasi (melalui environment variable)

| Variabel          | Default        | Keterangan |
|-------------------|----------------|------------|
| `HELPDESK_DB_PATH`| `./helpdesk.db`| Lokasi file database SQLite |
| `API_HOST`        | `0.0.0.0`     | Host server |
| `API_PORT`        | `5005`        | Port server |
| `API_DEBUG`       | `false`       | Mode debug Flask |

Contoh menjalankan dengan database lain / port lain (Windows PowerShell):

```powershell
$env:HELPDESK_DB_PATH = "G:\project_python\api_ithelpdesk\helpdesk.db"
$env:API_PORT = "8080"
python app.py
```

Linux / macOS:

```bash
HELPDESK_DB_PATH=/path/ke/helpdesk.db API_PORT=8080 python app.py
```

## Contoh penggunaan dari aplikasi lain

```bash
# Semua tiket selesai
curl http://localhost:5005/api/tiket

# Laporan bulanan Agustus 2026
curl "http://localhost:5005/api/tiket/bulanan?bulan=2026-08"
```