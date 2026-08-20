#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME=uvicorn-helpdeskit.service
SRC_DIR="$(dirname "$0")/../systemd"
SRC="$SRC_DIR/$SERVICE_NAME"
DST="/etc/systemd/system/$SERVICE_NAME"

if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run as root. Use: sudo $0"
  exit 1
fi

if [ ! -f "$SRC" ]; then
  echo "Unit file not found: $SRC"
  exit 1
fi

cp "$SRC" "$DST"
chmod 644 "$DST"
systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"
systemctl status "$SERVICE_NAME" --no-pager
