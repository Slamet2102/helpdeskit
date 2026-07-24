#!/usr/bin/env bash
#
# auto-start.sh — Dipanggil oleh cron @reboot untuk menjalankan server
# secara otomatis saat komputer restart.
#
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

LOG_FILE="$PROJECT_DIR/server.log"

# Hapus log lama jika terlalu besar (>5MB)
if [ -f "$LOG_FILE" ] && [ "$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)" -gt 5242880 ]; then
    : > "$LOG_FILE"
fi

echo "[$(date)] Starting Helpdesk IT RS..." >> "$LOG_FILE"

# Setup virtual environment
VENV_DIR="$PROJECT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# Install dependencies jika perlu
if ! python -c "import uvicorn" 2>/dev/null; then
    pip install --upgrade pip --quiet
    pip install fastapi uvicorn sqlalchemy jinja2 python-dotenv aiofiles httpx pydantic --quiet
fi

# Jalankan server di background
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "[$(date)] Server started with PID: $SERVER_PID" >> "$LOG_FILE"
echo "[$(date)] Access at http://localhost:8000" >> "$LOG_FILE"
