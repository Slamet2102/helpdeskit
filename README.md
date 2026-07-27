Helpdesk IT Rumah Sakit
=======================

Singkat
------
Aplikasi pencatatan tiket kerusakan hardware & jaringan untuk rumah sakit.
Backend: FastAPI, DB: SQLite, ORM: SQLAlchemy, WA notifications via WAHA.

Persyaratan
----------
- Python 3.11+ (Python 3.13 did work here after upgrading SQLAlchemy)
- Virtualenv
- WAHA service (example: http://localhost:3000/api)

Instalasi cepat
--------------
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Konfigurasi
-----------
Salin `.env` atau edit nilai di file `.env`:

- `DATABASE_URL` — SQLite default `sqlite:///./helpdesk.db`
- `UPLOAD_DIR` — direktori untuk file upload
- `WAHA_API_URL` — contoh: `http://localhost:3000/api`
- `WAHA_SESSION_NAME` — contoh: `default`
- `WAHA_GROUP_ID` — ID grup WhatsApp (mis. `120363000000000000@g.us`) jika ingin notifikasi grup
- `WAHA_IT_NUMBER` — nomor WhatsApp IT untuk fallback notifikasi langsung (mis. `6281234567890`)
- `WAHA_API_KEY` — API key WAHA (Anda set `12345`)

WAHA advanced config
--------------------
Beberapa deployment WAHA mungkin mengharapkan API key pada header khusus, di body, atau di query string.
Gunakan env berikut jika notifikasi menghasilkan `401 Unauthorized`:

- `WAHA_API_KEY_IN`: `header`, `body`, atau `query` — lokasi untuk menyertakan API key.
- `WAHA_API_AUTH_HEADER_NAME`: nama header yang digunakan jika `WAHA_API_KEY_IN=header` (mis. `x-waha-key`).
- `WAHA_API_KEY_PARAM`: nama parameter untuk body/query (default `token`).

Contoh `.env` untuk header khusus:

```
WAHA_API_KEY_IN=header
WAHA_API_AUTH_HEADER_NAME=x-waha-key
WAHA_API_KEY=12345
```

Contoh curl tes (header):

```bash
curl -X POST "http://localhost:3000/api/default/messages" \
  -H "Content-Type: application/json" \
  -H "x-waha-key: 12345" \
  -d '{"chatId":"120363000000000000@g.us","text":"Tes"}'
```

Jika masih `401`, periksa log WAHA server untuk pesan kesalahan lebih rinci.

Database migration helper
-------------------------
Jika Anda menambahkan fitur baru yang memerlukan kolom DB (mis. `waha_sent`), jalankan skrip migrasi kecil berikut:

```bash
python3 scripts/migrate_db.py
```

Skrip ini idempotent dan hanya bekerja pada SQLite `DATABASE_URL`.
Menjalankan aplikasi
--------------------
Jalankan server:

```bash
./venv/bin/python -m uvicorn app.main:app --port 8000
```

Endpoint penting
----------------
- Health: `GET /api/health`
- Master: `GET /api/master/units`, `GET /api/master/kerusakan`
- Buat tiket: `POST /api/tiket/` (form-data)
- Daftar tiket: `GET /api/tiket`
- Detail tiket: `GET /api/tiket/{id}`
- Update status: `PUT /api/tiket/{id}/status` (JSON `{ "status": "On Progress", "catatan": "..." }`)

Contoh membuat tiket (curl):

```bash
curl -X POST http://127.0.0.1:8000/api/tiket/ \
  -F nama_pelapor='Budi' \
  -F no_whatsapp='628112345678' \
  -F unit_id=3 \
  -F kerusakan_id=4 \
  -F deskripsi='Contoh masalah'
```

Catatan WAHA
------------
- Pastikan `WAHA_API_URL`, `WAHA_SESSION_NAME`, dan `WAHA_API_KEY` benar.
- Jika WAHA merespon 401, periksa API key dan header otorisasi yang digunakan oleh WAHA.
- Flow notifikasi WAHA saat ini:
  - Saat user membuat tiket, sistem mengirim template konfirmasi ke nomor user.
  - Setelah tiket dibuat, sistem mengirim notifikasi ke `WAHA_GROUP_ID`; jika grup kosong/null, otomatis fallback ke `WAHA_IT_NUMBER`.
  - Saat teknisi mengubah status tiket, sistem mengirim status update ke nomor user yang membuat tiket.
  - Saat status berubah menjadi `Selesai`, sistem mengirim notifikasi ke nomor IT dan nomor user yang terdaftar pada tiket.

Langkah berikutnya
------------------
- Tambah test otomatis untuk endpoint utama
- UI/UX polish dan validasi form
- Deployment (systemd/docker)

# helpdeskit
