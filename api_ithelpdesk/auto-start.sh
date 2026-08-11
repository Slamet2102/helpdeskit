#!/usr/bin/env bash
#
# auto-start.sh (api_ithelpdesk) — Menjalankan API Helpdesk (Flask, port 5005)
# otomatis saat komputer nyala/restart.
#
# Dipanggil oleh:
#   - cron @reboot (lewat auto-start.sh di root project)
#   - atau manual:  ./auto-start.sh
#
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

LOG_FILE="$PROJECT_DIR/api.log"

# Hapus log lama jika terlalu besar (>5MB)
if [ -f "$LOG_FILE" ] && [ "$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)" -gt 5242880 ]; then
    : > "$LOG_FILE"
fi

echo "[$(date)] Starting API Helpdesk (Flask)..." >> "$LOG_FILE"

# Setup virtual environment
VENV_DIR="$PROJECT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# Install dependencies jika perlu
if ! python -c "import flask" 2>/dev/null; then
    pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet
fi

# Jalankan API di background (nohup agar tetap hidup setelah script selesai)
nohup python app.py >> "$LOG_FILE" 2>&1 &
API_PID=$!
sleep 2

# Ambil port sebenarnya dari config (mendukung overrides API_PORT/.env)
API_PORT_ACTUAL="$(python -c 'import config; print(config.PORT)' 2>/dev/null || echo 5005)"

# Cek apakah proses API masih hidup — jika langsung mati (mis. port sudah
# dipakai proses lain), beri peringatan yang jelas di log.
if kill -0 "$API_PID" 2>/dev/null; then
    echo "[$(date)] API started OK with PID: $API_PID" >> "$LOG_FILE"
    echo "[$(date)] Access at http://localhost:${API_PORT_ACTUAL}" >> "$LOG_FILE"
else
    echo "[$(date)] WARNING: API gagal jalan (PID $API_PID sudah mati)." >> "$LOG_FILE"
    echo "[$(date)]          Kemungkinan port ${API_PORT_ACTUAL} sudah dipakai proses lain." >> "$LOG_FILE"
fi