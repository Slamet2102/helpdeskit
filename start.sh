#!/usr/bin/env bash
#
# start.sh — Jalankan semua project Helpdesk IT Rumah Sakit
# Cukup double-click / execute file ini dari terminal.
#
set -e

# Warna untuk output
H_RED='\033[0;31m'
H_GREEN='\033[0;32m'
H_YELLOW='\033[1;33m'
H_CYAN='\033[0;36m'
H_BOLD='\033[1m'
H_RESET='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo -e "${H_CYAN}${H_BOLD}"
echo "========================================"
echo "  Helpdesk IT Rumah Sakit"
echo "  Starting all services..."
echo "========================================"
echo -e "${H_RESET}"

# -----------------------------------------------------------
# 0. Cek Network & Firewall
# -----------------------------------------------------------
echo -e "${H_YELLOW}[INFO]${H_RESET} Mengecek koneksi jaringan..."

SERVER_IP=""
# Cari IP lokal di jaringan 192.168.x.x atau 10.x.x.x
for IP in $(hostname -I 2>/dev/null); do
    case "$IP" in
        192.*|10.*|172.*)
            SERVER_IP="$IP"
            break
            ;;
    esac
done

if [ -z "$SERVER_IP" ]; then
    # Fallback: ambil IP pertama yang bukan loopback
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
fi

if [ -n "$SERVER_IP" ]; then
    echo -e "${H_GREEN}[OK]${H_RESET} IP Server: ${H_BOLD}${SERVER_IP}${H_RESET}"
    echo -e "  Dari komputer lain buka: ${H_BOLD}http://${SERVER_IP}:8000${H_RESET}"
else
    echo -e "${H_RED}[WARNING]${H_RESET} Tidak bisa deteksi IP server."
    SERVER_IP="0.0.0.0"
fi

# Cek apakah port 8000 sudah bisa diakses dari luar dengan test bind
python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.bind(('0.0.0.0', 8000))
    s.close()
    print('[OK] Port 8000 tersedia.')
except OSError as e:
    if 'Address already in use' in str(e):
        print('[OK] Port 8000 sudah dipakai (server mungkin sudah jalan).')
    else:
        print(f'[WARNING] {e}')
" 2>/dev/null || echo -e "${H_YELLOW}[INFO]${H_RESET} Port check skipped."

echo ""

# -----------------------------------------------------------
# 1. Virtual Environment
# -----------------------------------------------------------
VENV_DIR=".venv"
PYTHON_BIN="python3"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${H_YELLOW}[INFO]${H_RESET} Virtual environment tidak ditemukan. Membuat baru..."
    $PYTHON_BIN -m venv "$VENV_DIR"
    echo -e "${H_GREEN}[OK]${H_RESET} Virtual environment created."
fi

source "$VENV_DIR/bin/activate"

# -----------------------------------------------------------
# 2. Install dependencies (jika belum)
# -----------------------------------------------------------
echo -e "${H_YELLOW}[INFO]${H_RESET} Memeriksa dependencies..."

# Cek apakah uvicorn sudah terinstall
if ! python -c "import uvicorn" 2>/dev/null; then
    echo -e "${H_YELLOW}[INFO]${H_RESET} Menginstall dependencies..."
    pip install --upgrade pip --quiet
    pip install \
        fastapi \
        uvicorn \
        sqlalchemy \
        jinja2 \
        python-dotenv \
        aiofiles \
        httpx \
        pydantic \
        fpdf2 \
        --quiet
    echo -e "${H_GREEN}[OK]${H_RESET} Dependencies installed."
else
    echo -e "${H_GREEN}[OK]${H_RESET} Semua dependencies sudah tersedia."
fi

# -----------------------------------------------------------
# 3. Jalankan Aplikasi
# -----------------------------------------------------------
echo ""
echo -e "${H_CYAN}${H_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${H_RESET}"
echo -e "${H_GREEN}${H_BOLD}  SERVER SIAP! Akses dari komputer lain:${H_RESET}"
echo -e "${H_CYAN}${H_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${H_RESET}"
echo -e "  URL Server:    ${H_BOLD}http://${SERVER_IP}:8000${H_RESET}"
echo -e "  Dari lokal:    ${H_BOLD}http://localhost:8000${H_RESET}"
echo -e "  Docs API:      ${H_BOLD}http://${SERVER_IP}:8000/docs${H_RESET}"
echo -e ""
echo -e "  ${H_YELLOW}⚠️  Jika komputer lain tidak bisa akses:${H_RESET}"
echo -e "  1. Pastikan komputer masih 1 jaringan WiFi/LAN yang sama"
echo -e "  2. Matikan firewall dengan perintah:"
echo -e "     ${H_BOLD}sudo ufw disable${H_RESET}"
echo -e "     atau buka port 8000:"
echo -e "     ${H_BOLD}sudo ufw allow 8000/tcp${H_RESET}"
echo -e "${H_CYAN}${H_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${H_RESET}"
echo ""
echo -e "${H_YELLOW}Tekan Ctrl+C untuk menghentikan server.${H_RESET}"
echo ""

# Jalankan menggunakan uvicorn langsung (sama seperti run.py)
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
