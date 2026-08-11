"""
API REST Helpdesk - mengirimkan data tiket dari database SQLite.

Endpoints:
  GET /                       -> info API & daftar endpoint
  GET /api/tables             -> daftar semua tabel di database
  GET /api/status             -> ringkasan jumlah tiket 'selesai'
  GET /api/tiket              -> semua tiket berstatus 'selesai'
  GET /api/tiket/<id>         -> satu tiket (hanya yang 'selesai')
  GET /api/tiket/bulanan?bulan=YYYY-MM   -> laporan bulanan (date, num, denum)
"""
import re

from flask import Flask, jsonify, request

import config
import db

app = Flask(__name__)

# Regex validasi bulan: format YYYY-MM
POLA_BULAN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _gagal(pesan: str, status: int = 400):
    """Helper untuk membuat response error JSON."""
    return jsonify({"error": pesan}), status


@app.after_request
def _tambah_cors(response):
    """Izinkan aplikasi lain (web/desktop) memanggil API dari origin berbeda."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.errorhandler(db.DatabaseError)
def _err_db(exc):
    return _gagal(str(exc), 500)


@app.get("/")
def index():
    return jsonify(
        {
            "nama": "API Helpdesk",
            "versi": "1.0.0",
            "database": config.DB_PATH,
            "endpoints": {
                "daftar_tabel": "/api/tables",
                "status": "/api/status",
                "semua_tiket_selesai": "/api/tiket",
                "tiket_by_id": "/api/tiket/{id}",
                "laporan_bulanan": "/api/tiket/bulanan?bulan=YYYY-MM",
            },
            "contoh": {
                "laporan_bulanan": "/api/tiket/bulanan?bulan=2026-08",
            },
        }
    )


@app.get("/api/tables")
def api_tabel():
    """Daftar semua tabel yang ada di database."""
    try:
        return jsonify({"tabel": db.daftar_tabel()})
    except db.DatabaseError as exc:
        return _gagal(str(exc), 500)


@app.get("/api/status")
def api_status():
    """Ringkasan jumlah tiket yang status-nya 'selesai'."""
    try:
        return jsonify(db.ringkasan())
    except db.DatabaseError as exc:
        return _gagal(str(exc), 500)


@app.get("/api/tiket")
def api_tiket_semua():
    """Semua data tabel tiket yang berstatus 'selesai'."""
    try:
        data = db.tiket_selesai()
        return jsonify({"jumlah": len(data), "data": data})
    except db.DatabaseError as exc:
        return _gagal(str(exc), 500)


@app.get("/api/tiket/<int:id_tiket>")
def api_tiket_satu(id_tiket: int):
    """Satu tiket berdasarkan id (hanya dikembalikan jika status = 'selesai')."""
    try:
        data = db.tiket_by_id(id_tiket)
    except db.DatabaseError as exc:
        return _gagal(str(exc), 500)
    if data is None:
        return _gagal(f"Tiket {id_tiket} tidak ditemukan / status bukan 'selesai'.", 404)
    return jsonify(data)


@app.get("/api/tiket/bulanan")
def api_laporan_bulanan():
    """
    Laporan bulanan per tanggal.

    Query param wajib: bulan=YYYY-MM (contoh: bulan=2026-08)

    Response langsung berupa array data (tanpa bungkus bulan):
    [
      { "date": "2026-08-01", "num": 1, "denum": 4 },
      ...
    ]
    diman:
      date  -> tanggal (dari kolom tanggal tiket)
      num   -> jumlah tiket 'selesai' di tanggal tsb dengan durasi_menit >= 60
      denum -> jumlah SEMUA tiket 'selesai' yang masuk pada tanggal tsb
    """
    bulan = request.args.get("bulan", "").strip()
    if not POLA_BULAN.match(bulan):
        return _gagal(
            "Parameter 'bulan' wajib dengan format YYYY-MM, contoh: bulan=2026-08"
        )
    try:
        data = db.laporan_bulanan(bulan)
        return jsonify(data)
    except db.DatabaseError as exc:
        return _gagal(str(exc), 500)


if __name__ == "__main__":
    print(f"API Helpdesk berjalan di http://{config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)