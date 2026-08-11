"""
Konfigurasi aplikasi API Helpdesk.

Semua nilai bisa di-override lewat environment variable, sehingga
aplikasi bisa dijalankan di server Windows maupun Linux tanpa ubah kode.
"""
import os
from pathlib import Path

# Direktori tempat aplikasi ini berada
BASE_DIR = Path(__file__).resolve().parent


def _muat_env():
    """
    Memuat file .env (jika ada) tanpa dependensi python-dotenv.

    Format yang didukung: BARIS_KUNCI=nilai (nilai boleh berisi spasi,
    tanda kutip dihilangkan). Baris kosong / komentar (#) dilewati.
    Variabel yang sudah ada di environment TIDAK ditimpa.
    """
    env_file = BASE_DIR / ".env"
    if not env_file.is_file():
        return
    for baris in env_file.read_text(encoding="utf-8").splitlines():
        baris = baris.strip()
        if not baris or baris.startswith("#") or "=" not in baris:
            continue
        kunci, _, nilai = baris.partition("=")
        kunci = kunci.strip()
        nilai = nilai.strip().strip('"').strip("'")
        if kunci and kunci not in os.environ:
            os.environ[kunci] = nilai


_muat_env()

# Lokasi file database SQLite (default: helpdesk.db di folder project)
# Bisa diubah lewat env: HELPDESK_DB_PATH
DB_PATH = os.environ.get("HELPDESK_DB_PATH", str(BASE_DIR / "helpdesk.db"))

# Host & port server. Default bind semua interface agar bisa diakses aplikasi lain
HOST = os.environ.get("API_HOST", "0.0.0.0")
PORT = int(os.environ.get("API_PORT", "5005"))
DEBUG = os.environ.get("API_DEBUG", "false").lower() in ("1", "true", "yes")

# Status tiket yang dikirimkan API (hanya data yang selesai)
STATUS_SELESAI = "selesai"

# Ambang batas durasi (menit) yang dihitung sebagai "num"
AMBANG_DURASI_MENIT = 60