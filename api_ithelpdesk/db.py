"""
Lapisan akses database SQLite (read-only).
Semua query memakai parameter binding untuk keamanan (anti SQL injection).
"""
import sqlite3
from contextlib import contextmanager
from typing import Optional

import config
from config import DB_PATH


class DatabaseError(Exception):
    """Gagal mengakses database."""


@contextmanager
def get_connection():
    """Context manager koneksi SQLite. Membuka koneksi baru per request."""
    con = None
    try:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        yield con
        con.commit()
    except sqlite3.Error as exc:
        if con is not None:
            con.rollback()
        raise DatabaseError(f"Gagal mengakses database: {exc}") from exc
    finally:
        if con is not None:
            con.close()


def daftar_tabel():
    """Mengembalikan daftar semua tabel di database."""
    with get_connection() as con:
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    return [r["name"] for r in rows]


def tiket_selesai(status: str = config.STATUS_SELESAI) -> list[dict]:
    """
    Mengembalikan SEMUA baris tabel tiket yang berstatus 'selesai'
    (case-insensitive), sekaligus menggabungkan data unit & jenis kerusakan.
    """
    with get_connection() as con:
        rows = con.execute(
            """
            SELECT t.id, t.nomor_tiket, t.tanggal, t.nama_pelapor,
                   t.no_whatsapp, t.unit_id, u.nama_unit AS nama_unit,
                   t.kerusakan_id, jk.nama_kerusakan AS nama_kerusakan,
                   t.deskripsi, t.status, t.durasi_menit, t.durasi
            FROM tiket t
            LEFT JOIN unit u ON u.id = t.unit_id
            LEFT JOIN jenis_kerusakan jk ON jk.id = t.kerusakan_id
            WHERE LOWER(COALESCE(t.status, '')) = LOWER(?)
            ORDER BY t.tanggal
            """,
            (status,),
        ).fetchall()
    return [dict(r) for r in rows]


def tiket_by_id(id_tiket: int, status: str = config.STATUS_SELESAI) -> Optional[dict]:
    """Mengambalikan satu tiket (hanya jika status = selesai) berdasarkan id."""
    with get_connection() as con:
        row = con.execute(
            """
            SELECT t.id, t.nomor_tiket, t.tanggal, t.nama_pelapor,
                   t.no_whatsapp, t.unit_id, u.nama_unit AS nama_unit,
                   t.kerusakan_id, jk.nama_kerusakan AS nama_kerusakan,
                   t.deskripsi, t.status, t.is_archived,
                   t.durasi_menit, t.durasi
            FROM tiket t
            LEFT JOIN unit u ON u.id = t.unit_id
            LEFT JOIN jenis_kerusakan jk ON jk.id = t.kerusakan_id
            WHERE t.id = ? AND LOWER(COALESCE(t.status, '')) = LOWER(?)
            """,
            (id_tiket, status),
        ).fetchone()
    return dict(row) if row else None


def laporan_bulanan(bulan: str, status: str = config.STATUS_SELESAI) -> list[dict]:
    """
    Laporan per tanggal dalam satu bulan (format parameter: 'YYYY-MM').

    Setiap baris:
      - date  : tanggal (YYYY-MM-DD) dari kolom `tanggal`
      - num   : jumlah tiket SUKSES/SUDAH SELESAI pada tanggal itu
                yang durasi_menit-nya >= AMBANG_DURASI_MENIT (>= 60 menit)
      - denum : jumlah SEMUA tiket 'selesai' yang masuk pada tanggal itu

    Hanya tiket yang status = 'selesai' yang dihitung.
    """
    with get_connection() as con:
        rows = con.execute(
            """
            SELECT SUBSTR(t.tanggal, 1, 10) AS tgl,
                   SUM(CASE WHEN t.durasi_menit >= ? THEN 1 ELSE 0 END) AS num,
                   COUNT(*) AS denum
            FROM tiket t
            WHERE LOWER(COALESCE(t.status, '')) = LOWER(?)
              AND SUBSTR(t.tanggal, 1, 7) = ?
            GROUP BY tgl
            ORDER BY tgl
            """,
            (config.AMBANG_DURASI_MENIT, status, bulan),
        ).fetchall()
    # Normalisasi hasil: pastikan tanggal tidak null (mis. tanggal kosong di db)
    hasil = []
    for r in rows:
        hasil.append(
            {
                "date": r["tgl"],
                "num": int(r["num"] or 0),
                "denum": int(r["denum"] or 0),
            }
        )
    return hasil


def ringkasan(status: str = config.STATUS_SELESAI) -> dict:
    """Ringkasan singkat: jumlah tiket dengan status tertentu."""
    with get_connection() as con:
        hitung = con.execute(
            "SELECT COUNT(*) AS jum FROM tiket WHERE LOWER(COALESCE(status,'')) = LOWER(?)",
            (status,),
        ).fetchone()["jum"]
    return {"status": status, "jumlah_tiket_selesai": hitung}