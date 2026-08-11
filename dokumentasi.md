# 📋 Dokumentasi — Helpdesk IT Rumah Sakit

Dokumentasi lengkap untuk aplikasi pencatatan tiket kerusakan hardware & jaringan di rumah sakit.

---

## Daftar Isi

1. [Ringkasan](#1-ringkasan)
2. [Fitur-fitur](#2-fitur-fitur)
3. [Teknologi & Dependensi](#3-teknologi--dependensi)
4. [Struktur Proyek](#4-struktur-proyek)
5. [Persyaratan Sistem](#5-persyaratan-sistem)
6. [Instalasi](#6-instalasi)
7. [Konfigurasi (.env)](#7-konfigurasi-env)
8. [Menjalankan Aplikasi](#8-menjalankan-aplikasi)
9. [Struktur Database](#9-struktur-database)
10. [Halaman (UI)](#10-halaman-ui)
11. [API Endpoint](#11-api-endpoint)
12. [Alur Notifikasi WhatsApp (WAHA)](#12-alur-notifikasi-whatsapp-waha)
13. [Fitur Export (CSV / PDF)](#13-fitur-export-csv--pdf)
14. [Autentikasi](#14-autentikasi)
15. [Migrasi Database](#15-migrasi-database)
16. [Testing](#16-testing)
17. [Troubleshooting](#17-troubleshooting)
18. [Roadmap / TODO](#18-roadmap--todo)

---

## 1. Ringkasan

**Helpdesk IT Rumah Sakit** adalah aplikasi berbasis web untuk mencatat dan mengelola tiket kerusakan
hardware dan jaringan di lingkungan rumah sakit. Aplikasi ini memungkinkan:

- Pelapor membuat tiket kerusakan (dengan foto).
- Teknisi IT mengubah status tiket (Open → On Progress → Pending → Selesai).
- Notifikasi otomatis via WhatsApp (menggunakan layanan **WAHA**).
- Dashboard dengan statistik KPI dan grafik tren.
- Export laporan ke **CSV** dan **PDF**.
- Arsip tiket lama dan kelola data master (unit, jenis kerusakan, user).

Selain aplikasi utama tersebut, repositori ini juga memuat **API REST Flask** terpisah
(`api_ithelpdesk/`) yang membaca **database yang sama** (`helpdesk.db`) dan memublikasikan
data tiket berstatus *selesai* ke aplikasi lain — dokumentasi endpoint ada di
[Bagian 11](#11-api-endpoint).

| | |
|---|---|
| **Backend** | FastAPI (Python) |
| **Database** | SQLite (SQLAlchemy ORM) |
| **Frontend** | Server-side templates (Jinja2) + Bootstrap + JavaScript |
| **Notifikasi** | WhatsApp via WAHA (WhatsApp HTTP API) |
| **Realtime** | Server-Sent Events (SSE) |
| **Autentikasi** | JWT (token + cookie) |

---

## 2. Fitur-fitur

| Fitur | Keterangan |
|---|---|
| 📝 **Pembuatan tiket** | Pelapor mengisi nama, no WhatsApp, unit, jenis kerusakan, deskripsi, dan foto |
| 🏷 **Status tiket** | `Open`, `On Progress`, `Pending`, `Selesai`, `Batal`, `Rusak` |
| ⏱ **Durasi pengerjaan** | Dihitung otomatis saat status berubah ke `On Progress` |
| 📊 **Dashboard KPI** | Total hari ini, Open, On Progress, Pending, Selesai |
| 📈 **Grafik tren** | Trend 7 hari terakhir |
| 📤 **Export laporan** | CSV & PDF (filter periode & filter lainnya) |
| 🔍 **Pencarian & filter** | Filter status, unit, pencarian nomor tiket/nama |
| ✅ **Checklist batch** | Pilih banyak tiket untuk arsipkan massal / export terpilih |
| 🗄 **Arsip tiket** | Soft-delete ke arsip, bisa dipulihkan/dihapus permanen |
| 🏢 **Master data** | Kelola Unit, Jenis Kerusakan (Hardware/Jaringan), dan User |
| 💬 **Notifikasi WhatsApp** | Konfirmasi tiket, notifikasi tiket baru, update status, notifikasi selesai |
| 🔔 **Realtime update** | Dashboard & daftar tiket ter-update otomatis via SSE |
| 🔐 **Login** | Autentikasi JWT dengan cookie (`admin` default) |

---

## 3. Teknologi & Dependensi

### Backend / Framework
- **Python** 3.11+ (dikembangkan & teruji pada Python 3.12)
- **FastAPI** 0.139.2
- **Uvicorn** 0.51.0 (ASGI server)

### Database & ORM
- **SQLAlchemy** 2.0.51
- **SQLite** (file `helpdesk.db`)

### Lainnya
- **Jinja2** 3.1.6 (template engine)
- **Pydantic** 2.13.4 (validasi/schema)
- **PyJWT** 2.13.0 (autentikasi JWT)
- **httpx** 0.28.1 (HTTP client untuk WAHA)
- **fpdf2** 2.8.7 (generasi PDF)
- **python-dotenv** 1.2.2 (baca file `.env`)
- **python-multipart** 0.0.32 (upload file / form-data)
- **aiofiles** 25.1.0 (file async)

> **Catatan:** Dependensi tidak didefinisikan dalam `requirements.txt`, melainkan diinstall
> langsung oleh skrip `start.sh` / `start.bat` / `auto-start.sh`. Pastikan **PyJWT** dan
> **python-multipart** ikut terinstall (keduanya wajib agar login & upload bekerja).

### API REST Flask (`api_ithelpdesk/`)
- **Flask** 3.1.3 — server REST API mandiri (default port **5005**), berbagi database
  yang sama dengan aplikasi utama (SQLite `helpdesk.db`).
- Memiliki venv & `requirements.txt` tersendiri di dalam folder `api_ithelpdesk/`.

---

## 4. Struktur Proyek

```
ITHelpdesk/
├── app/
│   ├── __init__.py
│   ├── main.py              # Entry point FastAPI, mounting router & halaman
│   ├── config.py            # Konfigurasi dari environment/.env
│   ├── database.py          # Engine SQLAlchemy, session, init_db (seed)
│   ├── models.py            # Model ORM (User, Unit, JenisKerusakan, Tiket, Progress)
│   ├── schemas.py           # Schema Pydantic (request/response)
│   ├── events.py            # EventManager untuk Server-Sent Events (SSE)
│   ├── waha.py              # Integrasi notifikasi WhatsApp via WAHA
│   └── routers/
│       ├── __init__.py
│       ├── auth.py          # Login/Logout/Verify (JWT)
│       ├── dashboard.py     # Statistik, trend, tiket per periode, import CSV
│       ├── master.py        # CRUD User, Unit, Jenis Kerusakan
│       └── tiket.py         # CRUD tiket, status, arsip, export, batch
├── api_ithelpdesk/          # API REST Flask (port 5005) — membaca helpdesk.db
│   ├── app.py               # Aplikasi Flask + endpoints
│   ├── config.py            # Konfigurasi (env/.env: API_HOST, API_PORT, HELPDESK_DB_PATH)
│   ├── db.py                # Akses SQLite read-only
│   ├── .env                 # HELPDESK_DB_PATH → ../helpdesk.db
│   ├── run.sh               # Jalankan manual (venv + python app.py)
│   ├── auto-start.sh        # Autostart API (dipanggil auto-start.sh root)
│   └── requirements.txt
├── scripts/
│   └── migrate_db.py        # Skrip migrasi kolom (idempotent)
├── static/
│   ├── css/style.css
│   └── js/main.js
├── templates/               # Halaman HTML (Jinja2)
│   ├── base.html
│   ├── index.html           # Dashboard
│   ├── daftar_tiket.html    # Daftar tiket
│   ├── tiket_form.html      # Form tiket baru
│   ├── tiket_detail.html    # Detail tiket
│   ├── master_data.html     # Kelola master data
│   ├── login.html           # Halaman login
│   └── archived_tiket.html  # Arsip tiket
├── tests/
│   ├── test_api.py
│   └── test_more.py
├── uploads/                 # Direktori upload foto tiket
├── helpdesk.db              # Database SQLite (otomatis dibuat)
├── .env                     # Konfigurasi (JANGAN commit)
├── .env.example             # Contoh konfigurasi
├── run.py                   # Entry point alternatif
├── start.sh                 # Skrip start Linux/macOS
├── start.bat                # Skrip start Windows
├── auto-start.sh            # Skrip autostart (cron @reboot)
├── start-helpdesk.desktop   # Shortcut desktop
├── check-network.sh         # Cek jaringan/firewall
├── dokumentasi.md           # Dokumentasi ini
└── README.md
```

---

## 5. Persyaratan Sistem

- **Python 3.11+** (teruji pada 3.12; versi 3.13 juga pernah dipakai setelah upgrade SQLAlchemy)
- **Virtualenv** (`.venv` atau `venv`)
- **WAHA service** berjalan — contoh: `http://localhost:3000/api`
- Untuk akses dari komputer lain: pastikan server & client dalam **satu jaringan** (WiFi/LAN)
  dan **port 8000** terbuka di firewall.
- **API REST Flask** (`api_ithelpdesk/`) berjalan terpisah di **port 5005** (default)
  — akses via `http://<IP-server>:5005`.

---

## 6. Instalasi

### Cara otomatis (disarankan)
Jalankan `start.sh` (Linux/macOS) atau `start.bat` (Windows) — skrip akan membuat
virtual environment, menginstall dependensi, dan menjalankan server.

### Cara manual
```bash
# 1. Masuk ke direktori proyek
cd ITHelpdesk

# 2. Buat virtual environment
python3 -m venv .venv

# 3. Aktifkan
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate.bat     # Windows

# 4. Install dependensi
pip install --upgrade pip
pip install fastapi uvicorn sqlalchemy jinja2 python-dotenv aiofiles httpx pydantic fpdf2 PyJWT python-multipart

# 5. Siapkan konfigurasi
cp .env.example .env             # lalu isi nilai sesuai kebutuhan

# 6. Jalankan
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 7. Konfigurasi (.env)

Salin `.env.example` menjadi `.env` lalu isi nilai sebenarnya. **Jangan commit** file `.env`.

| Variable | Default | Keterangan |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./helpdesk.db` | Lokasi database |
| `UPLOAD_DIR` | `./uploads` | Direktori upload foto |
| `BASE_URL` | `http://localhost:8000` | URL publik aplikasi (untuk link di notifikasi) |
| `SECRET_KEY` | `change-this-secret-key-in-production` | Kunci rahasia JWT — **ganti di produksi** |
| `WAHA_API_URL` | `http://localhost:3000/api` | URL service WAHA |
| `WAHA_SESSION_NAME` | `default` | Nama session WAHA |
| `WAHA_GROUP_ID` | *(kosong)* | ID grup WhatsApp (mis. `120363000000000000@g.us`) |
| `WAHA_IT_NUMBER` | *(kosong)* | Nomor IT fallback (mis. `6281234567890`) |
| `WAHA_API_KEY` | *(kosong)* | API key WAHA |
| `WAHA_API_AUTH_HEADER_NAME` | `X-Api-Key` | Nama header untuk API key |
| `WAHA_API_KEY_IN` | `header` | Lokasi API key: `header`, `body`, atau `query` |
| `WAHA_API_KEY_PARAM` | `token` | Nama param jika key dikirim via body/query |

### Contoh `.env`
```
DATABASE_URL=sqlite:///./helpdesk.db
UPLOAD_DIR=./uploads

WAHA_API_URL=http://localhost:3000/api
WAHA_SESSION_NAME=default
WAHA_GROUP_ID=
WAHA_API_KEY=12345
WAHA_API_AUTH_HEADER_NAME=X-Api-Key
WAHA_API_KEY_IN=header
WAHA_API_KEY_PARAM=token
WAHA_IT_NUMBER=6281234567890

BASE_URL=http://localhost:8000
SECRET_KEY=change-this-secret-key-in-production
```

---

## 8. Menjalankan Aplikasi

### Mode pengembangan (auto-reload)
```bash
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Mode produksi (tanpa reload)
```bash
nohup .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> server.log 2>&1 &
```

> ⚠️ **PENTING:** Server produksi berjalan **tanpa `--reload`**. Setiap perubahan kode Python
> mengharuskan **restart manual**:
> ```bash
> pkill -9 -f "uvicorn app.main:app"
> nohup .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> server.log 2>&1 &
> ```
> (Perubahan pada **template HTML** langsung aktif tanpa restart, karena Jinja2 memuat template dari disk setiap request.)

### Autostart saat reboot / startup

Saat komputer nyala atau restart, **cron `@reboot`** (user) memanggil `auto-start.sh`
yang menjalankan **dua service** sekaligus. Masing-masing punya log sendiri:

| Service | Port | Skrip | Log |
|---|---|---|---|
| Server utama (FastAPI/uvicorn) | 8000 | `auto-start.sh` | `server.log` |
| API REST (Flask) `api_ithelpdesk/` | 5005 | `api_ithelpdesk/auto-start.sh` | `api_ithelpdesk/api.log` |

- Baris cron:
  `@reboot /home/zabbix/ITHelpdesk/auto-start.sh > /home/zabbix/ITHelpdesk/cron.log 2>&1`
- `auto-start.sh` membuat `.venv` + menginstall dependensi jika belum ada, lalu
  menjalankan server utama di background (`nohup`).
- Kemudian memanggil `api_ithelpdesk/auto-start.sh` dengan **guard `||`** — jika API
  gagal start (mis. port 5005 sudah dipakai), server utama **tetap berjalan**.
- Kedua script memangkas log otomatis jika ukurannya > 5 MB.
- Restart manual setelah ubah kode: `pkill -9 -f "uvicorn app.main:app"` lalu `./auto-start.sh`.
- `start-helpdesk.desktop` — shortcut desktop untuk memulai aplikasi.

### Akses
- Aplikasi: `http://localhost:8000` (atau `http://<IP-server>:8000`)
- Dokumentasi API (Swagger): `http://localhost:8000/docs`
- Redoc: `http://localhost:8000/redoc`

---

## 9. Struktur Database

Database SQLite dibuat otomatis saat pertama kali server berjalan (`init_db`),
lengkap dengan seed data awal.

### Tabel `user`
| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | Integer (PK) | ID user |
| `username` | String(50), unique | Username |
| `password_hash` | String(255) | Password (saat ini plain text) |
| `role` | String(20) | Role (`admin` default) |
| `created_at` | DateTime | Waktu dibuat |

### Tabel `unit`
| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | Integer (PK) | ID unit |
| `nama_unit` | String(100), unique | Nama unit/ruangan |
| `status` | String(20) | Status (`Aktif` default) |

### Tabel `jenis_kerusakan`
| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | Integer (PK) | ID |
| `kategori` | String(20) | `Hardware` / `Jaringan` |
| `nama_kerusakan` | String(100) | Nama kerusakan |
| `status` | String(20) | Status (`Aktif` default) |

### Tabel `tiket`
| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | Integer (PK) | ID tiket |
| `nomor_tiket` | String(30), unique | Format `IT-YYYYMMDD-XXX` |
| `tanggal` | DateTime | Waktu dibuat |
| `nama_pelapor` | String(100) | Nama pelapor |
| `no_whatsapp` | String(20) | Nomor WhatsApp pelapor |
| `unit_id` | FK → `unit.id` | Unit/ruangan |
| `kerusakan_id` | FK → `jenis_kerusakan.id` | Jenis kerusakan |
| `deskripsi` | Text | Deskripsi masalah |
| `foto` | String(255) | Path foto (`/uploads/...`) |
| `status` | String(20) | `Open`, `On Progress`, `Pending`, `Selesai`, `Batal`, `Rusak` |
| `is_archived` | Boolean | Flag arsip (soft delete) |
| `durasi_menit` | Integer | Durasi pengerjaan dalam menit |
| `durasi` | String(10) | Durasi teks (mis. `1 jam 28 menit`) |

### Tabel `progress`
| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | Integer (PK) | ID |
| `tiket_id` | FK → `tiket.id` | Tiket terkait |
| `status` | String(20) | Status pada saat itu |
| `catatan` | Text | Catatan/riwayat (termasuk hasil notifikasi WAHA) |
| `waha_sent` | Boolean | Penanda apakah notifikasi WAHA dikirim |
| `tanggal` | DateTime | Waktu |

### Seed data otomatis
- **Admin:** `admin` / `admin`
- **Unit:** IGD, ICU, Laboratorium, Radiologi, Farmasi, Rawat Inap, Poli Umum, Kasir, Ruang Server, Administrasi
- **Kerusakan Hardware:** PC Tidak Menyala, PC Lambat, Monitor Rusak, Printer Tidak Bisa Print, Scanner Bermasalah, Keyboard Rusak, Mouse Rusak, UPS Bermasalah
- **Kerusakan Jaringan:** Internet Putus, WiFi Tidak Tersambung, LAN Tidak Berfungsi, Tidak Bisa Akses SIMRS, Server Tidak Bisa Diakses, Switch Bermasalah, Access Point Mati, IP Conflict

---

## 10. Halaman (UI)

| URL | Halaman | Keterangan |
|---|---|---|
| `/` | **Dashboard** | KPI, grafik tren 7 hari, laporan periode (tahun/bulan), tiket terbaru, export CSV |
| `/tiket/baru` | **Tiket Baru** | Form pembuatan tiket (foto + notifikasi WAHA) |
| `/tiket` | **Daftar Tiket** | Daftar + filter + pencarian + checklist batch + export CSV |
| `/tiket/{id}` | **Detail Tiket** | Detail tiket + riwayat progress + ubah status |
| `/tiket/arsip` | **Arsip** | Tiket yang diarsipkan (restore / hapus) |
| `/master` | **Master Data** | Kelola unit, jenis kerusakan, user |
| `/login` | **Login** | Halaman autentikasi |

---

## 11. API Endpoint

### Umum (main.py)
| Method | Endpoint | Keterangan |
|---|---|---|
| GET | `/api/health` | Cek kesehatan server |
| GET | `/api/events` | SSE realtime (event `tiket_baru`, `status_update`) |

### Autentikasi (`/api/auth`)
| Method | Endpoint | Keterangan |
|---|---|---|
| POST | `/api/auth/login` | Login → JWT + cookie (`auth_token`) |
| GET | `/api/auth/verify` | Verifikasi token (header `Authorization: Bearer ...`) |
| GET | `/api/auth/me` | Info user dari token |
| POST | `/api/auth/logout` | Logout (hapus cookie) |

### Dashboard (`/api/dashboard`)
| Method | Endpoint | Keterangan |
|---|---|---|
| GET | `/api/dashboard/stats` | Statistik KPI (query: `today=true/false`) |
| GET | `/api/dashboard/daily-summary` | Ringkasan harian untuk grafik (query: `days=7`) |
| GET | `/api/dashboard/tiket` | Tiket per periode (query: `year`, `month`) |
| GET | `/api/dashboard/waha-status` | Status koneksi WAHA |
| POST | `/api/dashboard/import` | Import tiket dari CSV (upload file) |

### Tiket (`/api/tiket`)
| Method | Endpoint | Keterangan |
|---|---|---|
| POST | `/api/tiket/` | Buat tiket (form-data: nama_pelapor, no_whatsapp, unit_id, kerusakan_id, deskripsi, foto) |
| GET | `/api/tiket/` | Daftar tiket (query: status, unit_id, search, today, sort_by, sort_order, page, limit) |
| GET | `/api/tiket/{id}` | Detail tiket |
| PUT | `/api/tiket/{id}/status` | Update status (JSON: `status`, `catatan`) |
| DELETE | `/api/tiket/{id}` | Arsipkan tiket (soft delete) |
| POST | `/api/tiket/batch/archive` | Arsipkan banyak tiket (JSON: `ids`) |
| GET | `/api/tiket/archive` | Daftar tiket arsip (query: search, page, limit) |
| POST | `/api/tiket/archive/{id}/restore` | Pulihkan tiket dari arsip |
| DELETE | `/api/tiket/archive` | Hapus permanen semua arsip |
| DELETE | `/api/tiket/archive/batch` | Hapus permanen arsip terpilih (JSON: `ids`) |
| GET | `/api/tiket/export` | **Export CSV/PDF** — endpoint export terpadu (detail di [bagian 13](#13-fitur-export-csv--pdf)) |

### Master Data (`/api/master`)
| Method | Endpoint | Keterangan |
|---|---|---|
| GET/POST | `/api/master/users` | List / buat user |
| PUT/DELETE | `/api/master/users/{id}` | Update / hapus user |
| GET/POST | `/api/master/units` | List / buat unit |
| PUT/DELETE | `/api/master/units/{id}` | Update / hapus unit |
| GET/POST | `/api/master/kerusakan` | List / buat jenis kerusakan (query kategori: Hardware/Jaringan) |
| PUT/DELETE | `/api/master/kerusakan/{id}` | Update / hapus jenis kerusakan |

### API REST Flask — `api_ithelpdesk` (port 5005)

Server Flask **mandiri** (terpisah dari FastAPI) yang membaca **database yang sama**
(`helpdesk.db`) dan memublikasikan data tiket berstatus **`selesai`** ke aplikasi
lain/jaringan. Default berjalan di `http://0.0.0.0:5005`.

| Method | Endpoint | Keterangan |
|---|---|---|
| GET | `/` | Info API & daftar endpoint |
| GET | `/api/tables` | Daftar semua tabel di database |
| GET | `/api/status` | Jumlah tiket berstatus `selesai` |
| GET | `/api/tiket` | Semua tiket berstatus `selesai` |
| GET | `/api/tiket/{id}` | Satu tiket (hanya yang `selesai`) |
| GET | `/api/tiket/bulanan?bulan=YYYY-MM` | Laporan bulanan per tanggal (`date`, `num`, `denum`) |

Konfigurasi via environment / `.env` (`api_ithelpdesk/.env`):

| Variable | Default | Keterangan |
|---|---|---|
| `HELPDESK_DB_PATH` | `./helpdesk.db` | Lokasi database (di sini diarahkan ke `../helpdesk.db`) |
| `API_HOST` | `0.0.0.0` | Host bind server |
| `API_PORT` | `5005` | Port server |
| `API_DEBUG` | `false` | Mode debug Flask |

Contoh penggunaan:

```bash
curl http://localhost:5005/api/status
curl "http://localhost:5005/api/tiket/bulanan?bulan=2026-08"
```

---

## 12. Alur Notifikasi WhatsApp (WAHA)

Notifikasi dikirim menggunakan service **WAHA** (WhatsApp HTTP API) dengan mekanisme
*failover* ke beberapa format endpoint.

### Endpoint WAHA yang dicoba (berurutan)
1. `POST {WAHA_API_URL}/sendText` — session + chatId di body
2. `POST {WAHA_API_URL}/sendText` — dengan token API key di body
3. `POST {WAHA_API_URL}/sendText` — dengan token API key di query string (jika `WAHA_API_KEY_IN=query`)

### Skenario notifikasi
| Skenario | Dikirim ke | Pesan |
|---|---|---|
| **Tiket baru dibuat** | Grup IT (`WAHA_GROUP_ID`) → fallback `WAHA_IT_NUMBER` | 🔔 *Tiket Baru* + detail |
| **Konfirmasi ke pelapor** | Nomor WhatsApp pelapor | ✅ *Tiket Anda Berhasil Dibuat* |
| **Status → On Progress** | Nomor pelapor | 🔧 Tiket sedang dikerjakan |
| **Status → Pending** | Nomor pelapor | ⏸ Tiket ditunda |
| **Status → Selesai** | Pelapor + Grup IT/IT number | ✅ *Tiket Selesai* + durasi |

### Format nomor WhatsApp
Nomor dinormalisasi otomatis:
- Diawali `0` → diganti `62` (contoh: `0812...` → `62812...`)
- Diawali `8` → ditambah `62` (contoh: `812...` → `62812...`)
- Ditambahkan suffix `@c.us` untuk chat personal

### Konfigurasi API key
Jika notifikasi menghasilkan `401 Unauthorized`, atur:
- `WAHA_API_KEY_IN=header` + `WAHA_API_AUTH_HEADER_NAME=x-waha-key` (header khusus)
- atau `WAHA_API_KEY_IN=body` / `query` dengan `WAHA_API_KEY_PARAM`

---

## 13. Fitur Export (CSV / PDF)

Export menggunakan **satu endpoint terpadu**: `GET /api/tiket/export`
(dipakai oleh halaman Dashboard dan Daftar Tiket).

### Parameter
| Parameter | Tipe | Keterangan |
|---|---|---|
| `year` | int | Filter periode (tahun). Wajib jika ingin filter bulan. |
| `month` | int (1-12) | Filter bulan (opsional, hanya jika `year` diisi) |
| `status` | str | Filter status |
| `unit_id` | int | Filter unit |
| `search` | str | Pencarian nomor tiket / nama pelapor |
| `today` | bool | Hanya tiket hari ini |
| `ids` | str | ID tiket terpilih dipisah koma (untuk export tiket tercentang) |
| `sort_by` | str | Kolom sorting (default `tanggal`) |
| `sort_order` | str | `asc` / `desc` |
| `format` | str | `csv` (default) atau `pdf` |

### Contoh
```bash
# Export semua tiket tahun 2026 (CSV)
curl -o laporan.csv "http://localhost:8000/api/tiket/export?year=2026&format=csv"

# Export tiket bulan Agustus 2026 (PDF)
curl -o laporan.pdf "http://localhost:8000/api/tiket/export?year=2026&month=8&format=pdf"

# Export tiket status Open (CSV)
curl -o open.csv "http://localhost:8000/api/tiket/export?status=Open&format=csv"
```

### Kolom CSV
```
id, nomor_tiket, tanggal, nama_pelapor, no_whatsapp, unit, kerusakan,
kategori, deskripsi, status, durasi, numerator, denumerator
```

### Aturan Numerator / Denumerator
- `durasi_menit >= 60` → **Numerator = 1**, Denumerator = 0
- `durasi_menit < 60` → Numerator = 0, **Denumerator = 1**
- `durasi_menit` kosong/tidak valid → 0, 0

### Tombol di UI
- **Dashboard** → tombol **CSV** di panel laporan (periode tahun/bulan).
- **Daftar Tiket** → tombol **Export CSV** selalu tampil; jika ada tiket tercentang
  akan export tiket terpilih (`ids=...`), jika tidak ada akan export semua hasil filter.

> **Catatan:** Endpoint lama `/api/dashboard/export` sudah **dihapus** dan digabung ke
> `/api/tiket/export` (2026-08-01).

---

## 14. Autentikasi

- Menggunakan **JWT (HS256)** dengan masa berlaku default **8 jam** (`ACCESS_TOKEN_EXPIRE_MINUTES = 480`).
- Setelah login, token disimpan di **cookie** `auth_token` (HttpOnly).
- Token juga bisa dikirim via header `Authorization: Bearer <token>`.
- User default: `admin` / `admin`.
- ⚠️ Saat ini password disimpan sebagai **plain text** — disarankan diganti dengan hashing
  (mis. `bcrypt`) untuk produksi.

---

## 15. Migrasi Database

Jika ada fitur baru yang menambah kolom, jalankan skrip migrasi:

```bash
python3 scripts/migrate_db.py
```

Skrip ini **idempotent** (aman dijalankan berulang) dan hanya mendukung SQLite.
Migrasi yang sudah ditangani:
- `progress.waha_sent` — penanda status notifikasi WAHA
- `tiket.durasi_menit` & `tiket.durasi` — durasi pengerjaan

Sebagian migrasi juga otomatis dilakukan oleh `init_db()` saat server start
(khusus SQLite, untuk kolom `waha_sent`, `is_archived`, dan `status`).

---

## 16. Testing

Direktori `tests/` berisi:
- `tests/test_api.py`
- `tests/test_more.py`

Untuk menjalankan (perlu `pytest` terinstall di environment):

```bash
.venv/bin/pip install pytest
.venv/bin/python -m pytest tests/ -q
```

---

## 17. Troubleshooting

### Server tidak bisa diakses dari komputer lain
1. Pastikan server & client dalam **satu jaringan** (WiFi/LAN sama).
2. Buka port 8000 di firewall:
   ```bash
   sudo ufw allow 8000/tcp
   # atau matikan firewall
   sudo ufw disable
   ```
3. Cek IP server dengan `hostname -I` lalu akses `http://<IP>:8000`.

### Notifikasi WhatsApp gagal / 401 Unauthorized
1. Pastikan `WAHA_API_URL`, `WAHA_SESSION_NAME`, `WAHA_API_KEY` benar.
2. Sesuaikan `WAHA_API_KEY_IN` dan `WAHA_API_AUTH_HEADER_NAME` dengan konfigurasi WAHA.
3. Periksa log server (`server.log`) untuk detail error.
4. Cek status koneksi WAHA via endpoint `/api/dashboard/waha-status`.

### Pesan tidak bisa dikirim ke GRUP WhatsApp (padahal `WAHA_GROUP_ID` terisi)
Penyebab umum (sudah diperbaiki 2026-08-01): ID grup berakhiran `@g.us` pernah **diubah
menjadi `@c.us`** oleh fungsi normalisasi nomor, sehingga WAHA tidak menemukan grup.
Pastikan:
1. `WAHA_GROUP_ID` di `.env` berformat benar dan berakhiran `@g.us`
   (contoh: `120363429175790043@g.us`).
2. Kode `_ensure_chat_id()`/`_normalize_whatsapp_number()` di `app/waha.py` **tidak**
   mengubah ID yang sudah berakhiran `@g.us`/`@c.us`.
3. Uji kirim langsung: `send_text('<group_id>', 'tes')` harus mengembalikan `True`.

> Catatan: Session WAHA bisa melaporkan `presence: "offline"` padahal status `WORKING`.
> Dashboard mungkin menampilkan "tidak terhubung" karena cek koneksi memerlukan
> `presence == "online"`, meskipun pengiriman pesan tetap berfungsi.

### Endpoint export menghasilkan 422
Pastikan endpoint export `/api/tiket/export` tidak tertimpa route dinamis —
route `GET /api/tiket/{tiket_id}` sudah menggunakan converter `:int`
(`/api/tiket/{tiket_id:int}`) sehingga `/export` tidak tertangkap sebagai ID.

### Ada banyak proses uvicorn berjalan
Selalu panggil `pkill -9 -f "uvicorn app.main:app"` lalu start ulang, dan verifikasi
hanya **satu** proses yang berjalan:
```bash
ps aux | grep "uvicorn app.main:app" | grep -v grep
```

### PDF export error `AttributeError: 'bytearray' object has no attribute 'encode'`
Sudah diperbaiki dengan membungkus hasil `fpdf` menggunakan `bytes(...)`.
Jika muncul lagi, pastikan kode menggunakan `bytes(_generate_pdf(...))`.

### Port 8000 sudah dipakai
Ganti port dengan parameter `--port <nomor>` atau gunakan `run.py`.

### Port 5005 (API Flask `api_ithelpdesk`) sudah dipakai
- Jika `api_ithelpdesk/api.log` menulis `Address already in use`, berarti port 5005
  masih dipegang proses lain (mis. hasil uji manual yang berjalan sebagai **root**,
  terlihat di `ps` sebagai `python3 app.py`).
- Saat reboot proses tersebut mati, dan `auto-start.sh` otomatis mengambil alih port 5005.
- Tanpa menunggu reboot: `sudo kill <PID>` lalu jalankan ulang `./auto-start.sh`.

---

## 18. Roadmap / TODO

Berdasarkan `TODO.md` dan README:

- [x] Fitur checklist & batch archive
- [x] Export CSV (tombol selalu tampil di daftar tiket)
- [x] Endpoint export terpadu (Dashboard + Daftar Tiket)
- [ ] Tambah test otomatis untuk endpoint utama
- [ ] UI/UX polish & validasi form
- [ ] Deployment (systemd/docker)
- [ ] Hashing password (bcrypt) untuk produksi
- [ ] Export PDF di UI (backend sudah mendukung)

---

*Dokumen ini dibuat otomatis dari struktur dan kode project (terakhir diperbarui 2026-08-11 — penambahan API REST Flask `api_ithelpdesk/` & autostart dua service).*
