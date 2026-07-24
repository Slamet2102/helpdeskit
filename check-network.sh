#!/usr/bin/env bash
#
# check-network.sh — Diagnostik konektivitas untuk Helpdesk IT RS
# Jalankan ketika komputer lain tidak bisa akses server
#
set -e

H_RED='\033[0;31m'
H_GREEN='\033[0;32m'
H_YELLOW='\033[1;33m'
H_CYAN='\033[0;36m'
H_BOLD='\033[1m'
H_RESET='\033[0m'

SERVER_IP=$(hostname -I 2>/dev/null | grep -oE '192\.168\.[0-9]+\.[0-9]+|10\.[0-9]+\.[0-9]+\.[0-9]+|172\.1[6-9]\.[0-9]+\.[0-9]+' | head -1)
if [ -z "$SERVER_IP" ]; then
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
fi

echo -e "${H_CYAN}${H_BOLD}"
echo "=========================================="
echo "  Diagnostik Jaringan - Helpdesk IT RS"
echo "=========================================="
echo -e "${H_RESET}"

echo -e "${H_YELLOW}[1]${H_RESET} IP Server ini: ${H_BOLD}$SERVER_IP${H_RESET}"
echo ""

echo -e "${H_YELLOW}[2]${H_RESET} Cek apakah port 8000 sudah bind ke 0.0.0.0..."
ss -tlnp 2>/dev/null | grep 8000 || echo -e "  ${H_RED}[ERROR] Port 8000 tidak terdengar!${H_RESET}"
echo ""

echo -e "${H_YELLOW}[3]${H_RESET} Tes koneksi dari lokal (harus sukses)..."
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ | grep -q 200; then
    echo -e "  ${H_GREEN}[OK] http://127.0.0.1:8000 — bisa diakses${H_RESET}"
else
    echo -e "  ${H_RED}[ERROR] Server tidak merespon di localhost!${H_RESET}"
fi

echo -e "${H_YELLOW}[4]${H_RESET} Tes koneksi dari IP server..."
if curl -s -o /dev/null -w "%{http_code}" http://$SERVER_IP:8000/ | grep -q 200; then
    echo -e "  ${H_GREEN}[OK] http://$SERVER_IP:8000 — bisa diakses${H_RESET}"
else
    echo -e "  ${H_RED}[ERROR] Server tidak merespon di $SERVER_IP!${H_RESET}"
fi
echo ""

echo -e "${H_YELLOW}[5]${H_RESET} Cek firewall..."
if command -v ufw &>/dev/null; then
    UFW_STATUS=$(sudo ufw status 2>/dev/null | head -1 || echo "inactive")
    echo -e "  Status UFW: ${H_BOLD}$UFW_STATUS${H_RESET}"
    if echo "$UFW_STATUS" | grep -qi "active"; then
        echo -e "  ${H_RED}⚠️  Firewall AKTIF! Bisa blokir akses dari komputer lain.${H_RESET}"
        echo -e "  Solusi: jalankan perintah:"
        echo -e "    ${H_BOLD}sudo ufw allow 8000/tcp${H_RESET}"
        echo -e "    atau ${H_BOLD}sudo ufw disable${H_RESET}"
    fi
else
    echo -e "  UFW tidak terinstall"
fi

if command -v firewall-cmd &>/dev/null; then
    FW_ZONE=$(sudo firewall-cmd --list-ports 2>/dev/null || echo "")
    if echo "$FW_ZONE" | grep -q "8000"; then
        echo -e "  ${H_GREEN}[OK] Port 8000 sudah terbuka di firewalld${H_RESET}"
    else
        echo -e "  ${H_YELLOW}[INFO] Port 8000 mungkin belum terbuka di firewalld${H_RESET}"
        echo -e "  Solusi:"
        echo -e "    ${H_BOLD}sudo firewall-cmd --add-port=8000/tcp --permanent${H_RESET}"
        echo -e "    ${H_BOLD}sudo firewall-cmd --reload${H_RESET}"
    fi
fi

echo ""
echo -e "${H_YELLOW}[6]${H_RESET} Info untuk akses dari komputer LAIN:"
echo -e "  Buka browser dan ketik: ${H_BOLD}http://$SERVER_IP:8000${H_RESET}"
echo -e ""
echo -e "  ${H_RED}Jika tetap tidak bisa:${H_RESET}"
echo -e "  1. Pastikan kedua komputer dalam SATU jaringan yang sama"
echo -e "     (cek WiFi/LAN, harus satu router/switch)"
echo -e "  2. Cek firewall seperti langkah [5] di atas"
echo -e "  3. Coba matikan firewall total (sementara):"
echo -e "     ${H_BOLD}sudo ufw disable${H_RESET}"
echo -e "     lalu test akses lagi"
echo -e "  4. Cek apakah ada anti-virus yang blokir port"
echo -e ""
echo -e "${H_CYAN}${H_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${H_RESET}"
