Cloudflare Tunnel — Setup & Run

Dokumentasi ini menjelaskan langkah untuk menjalankan Cloudflare Tunnel yang sudah disiapkan di folder ini.

Lokasi penting
- `config.yml`: `/home/zabbix/ITHelpdesk/cloudflare/config.yml`
- Credentials (tunnel): `/home/zabbix/ITHelpdesk/cloudflare/<TUNNEL_ID>.json`
- Log tunnel: `/home/zabbix/ITHelpdesk/cloudflare/tunnel.log`

Persyaratan
- `cloudflared` terinstal di `/usr/local/bin/cloudflared`.
- User yang menjalankan service: `zabbix` (atau ganti di unit file jika berbeda).

Langkah cepat (jalankan sebagai user biasa untuk file, gunakan `sudo` untuk service)

1. Pastikan file konfigurasi dan credentials ada:

```bash
ls -l /home/zabbix/ITHelpdesk/cloudflare/config.yml
ls -l /home/zabbix/ITHelpdesk/cloudflare/*.json
```

2. Tes koneksi lokal aplikasi (harus merespon 200):

```bash
curl -sS http://127.0.0.1:8000/api/health
```

3. Jalankan tunnel sekali untuk tes:

```bash
/usr/local/bin/cloudflared tunnel --config /home/zabbix/ITHelpdesk/cloudflare/config.yml run <TUNNEL_ID>
```

Systemd service (auto-start pada boot)

Service sudah disiapkan sebagai `cloudflared@<name>.service` pada contoh `helpdeskit-tunnel`.
Jika belum ada, buat file unit berikut sebagai root di `/etc/systemd/system/cloudflared@helpdeskit-tunnel.service`:

```ini
[Unit]
Description=cloudflared tunnel %i
After=network.target

[Service]
Type=simple
User=zabbix
Environment=HOME=/home/zabbix
ExecStart=/usr/local/bin/cloudflared tunnel --config /home/zabbix/ITHelpdesk/cloudflare/config.yml run %i
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable & start service (jalankan sekali sebagai root / user dengan sudo):

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cloudflared@helpdeskit-tunnel
sudo systemctl status cloudflared@helpdeskit-tunnel --no-pager
sudo journalctl -u cloudflared@helpdeskit-tunnel -f
```

Memberi izin manajemen service tanpa password (opsional)

Jika Anda ingin user `zabbix` mengelola service tanpa memasukkan password sudo, buat file sudoers drop-in:

```bash
sudo tee /etc/sudoers.d/cloudflared > /dev/null <<'EOF'
# Allow zabbix to manage the cloudflared service (no password)
zabbix ALL=(root) NOPASSWD: /usr/bin/systemctl daemon-reload, /usr/bin/systemctl enable --now cloudflared@helpdeskit-tunnel, /usr/bin/systemctl start cloudflared@helpdeskit-tunnel, /usr/bin/systemctl status cloudflared@helpdeskit-tunnel, /usr/bin/journalctl -u cloudflared@helpdeskit-tunnel
EOF
sudo chmod 440 /etc/sudoers.d/cloudflared

# verify as zabbix
sudo -l -U zabbix
```

Verifikasi publik

- Pastikan DNS di Cloudflare menunjuk ke `CNAME <TUNNEL_ID>.cfargotunnel.com` dan record proxied (orange cloud).
- Tes dari perangkat eksternal:

```bash
curl -sS https://helpdeskit.biz.id/api/health
curl -sS https://helpdeskit.biz.id/ | head -n 40
```

Troubleshooting

- 404 publik: pastikan `ingress` di `config.yml` mencantumkan `hostname` yang persis sama dengan domain dan menunjuk ke `service` yang benar (contoh `http://192.168.0.150:8000`).
- Tunnel tidak hidup: cek journal/logs:

```bash
sudo journalctl -u cloudflared@helpdeskit-tunnel -n 200 --no-pager
tail -n 200 /home/zabbix/ITHelpdesk/cloudflare/tunnel.log
```

- Peringatan ICMP / ping_group_range: non-fatal. Untuk menghilangkan peringatan, tambahkan user ke grup yang sesuai atau set `net.ipv4.ping_group_range`:

```bash
# contoh menambah user ke grup netdev
sudo usermod -aG netdev zabbix

# atau set ping_group_range (persist)
echo "net.ipv4.ping_group_range = 65534 65534" | sudo tee /etc/sysctl.d/99-cloudflared.conf
sudo sysctl --system
```

Membersihkan proses cadangan

Jika terdapat proses `cloudflared` yang dijalankan oleh skrip wrapper/sandbox (terlihat beberapa proses dengan command berbeda), hentikan yang tidak perlu, lalu biarkan systemd mengelola proses:

```bash
# lihat proses
ps aux | grep cloudflared | grep -v grep

# hentikan proses user yang tidak diinginkan (periksa PID dulu)
kill <PID>

# atau restart service yang dikelola systemd
sudo systemctl restart cloudflared@helpdeskit-tunnel
```

Keamanan

- Jaga agar `TunnelSecret` dan API token Cloudflare tidak masuk ke repo publik. File kredensial disimpan di `/home/zabbix/ITHelpdesk/cloudflare/` — pastikan folder ini tidak dipush ke publik.

Jika butuh bantuan lanjutan, beri tahu langkah mana yang ingin saya jalankan atau monitoring yang Anda perlukan.
# Cloudflare Tunnel untuk Helpdesk IT Rumah Sakit

Panduan lengkap menghubungkan aplikasi Helpdesk IT ke domain `helpdeskit.biz.id` melalui Cloudflare Tunnel.

## 📋 Prasyarat

1. **Domain terdaftar** — `helpdeskit.biz.id` sudah terdaftar di registrar (mis. Niagahoster, IDCloudHost, dll.)
2. **Akun Cloudflare** — Anda punya akun di [dash.cloudflare.com](https://dash.cloudflare.com/)
3. **cloudflared terinstal** — Versi 2026.7.3 sudah tersedia di server ini
4. **Aplikasi berjalan** — Helpdesk IT berjalan di `http://localhost:8000`

## 🚀 Quick Start (Otomatis)

Jalankan script setup otomatis:

```bash
cd /home/zabbix/ITHelpdesk
chmod +x cloudflare/setup-tunnel.sh
./cloudflare/setup-tunnel.sh
```

Script ini akan:
- Membuka browser untuk login ke Cloudflare
- Membuat tunnel otomatis
- Membuat file konfigurasi di `~/.cloudflared/config.yml`
- Membuat systemd service
- Memulai tunnel

## 🔧 Manual Setup (Jika otomatis gagal)

### Langkah 1: Login ke Cloudflare

```bash
cloudflared tunnel login
```

Browser akan terbuka. Login ke akun Cloudflare Anda dan pilih domain `helpdeskit.biz.id`.

### Langkah 2: Buat Tunnel

```bash
cloudflared tunnel create helpdeskit-tunnel
```

Output akan menampilkan **Tunnel UUID** dan path credentials file, misalnya:

```
Created tunnel helpdeskit-tunnel with id abc123-def456-... 
Credentials written to ~/.cloudflared/abc123-def456-....json
```

### Langkah 3: Buat File Konfigurasi

Salin template dan edit:

```bash
cp cloudflare/config.yml.example ~/.cloudflared/config.yml
```

Edit `~/.cloudflared/config.yml` dan ganti `YOUR-TUNNEL-UUID-HERE` dengan UUID dari Langkah 2.

### Langkah 4: Hubungkan Domain ke Tunnel

Di **Cloudflare Dashboard** → **DNS** → tambahkan record:

| Type | Name | Content | Proxy status |
|------|------|---------|-------------|
| CNAME | helpdeskit.biz.id | `<UUID>.cfargotunnel.com` | Proxied (oranye) |
| CNAME | www.helpdeskit.biz.id | `<UUID>.cfargotunnel.com` | Proxied (oranye) |

> **Catatan:** Jika domain belum menggunakan nameserver Cloudflare, Anda perlu mengarahkan nameserver domain ke Cloudflare terlebih dahulu. Hubungi registrar Anda untuk mengganti nameserver ke:
> - `lara.ns.cloudflare.com`
> - `leo.ns.cloudflare.com`

### Langkah 5: Buat Systemd Service

```bash
sudo tee /etc/systemd/system/cloudflared@helpdeskit-tunnel.service > /dev/null << 'EOF'
[Unit]
Description=Cloudflare Tunnel (helpdeskit-tunnel)
After=network.target

[Service]
Type=simple
User=zabbix
ExecStart=/usr/local/bin/cloudflared tunnel --config /home/zabbix/.cloudflared/config.yml run
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable cloudflared@helpdeskit-tunnel
sudo systemctl start cloudflared@helpdeskit-tunnel
```

### Langkah 6: Verifikasi

```bash
# Cek status service
sudo systemctl status cloudflared@helpdeskit-tunnel

# Cek tunnel list
cloudflared tunnel list

# Cek log
sudo journalctl -u cloudflared@helpdeskit-tunnel -f
```

## ⚙️ Konfigurasi Tambahan

### HTTPS di Aplikasi

Cloudflare Tunnel otomatis memberikan HTTPS. Pastikan aplikasi Anda menghandle redirect HTTP → HTTPS dengan benar. Di `app/config.py`, `BASE_URL` sudah diupdate ke `https://helpdeskit.biz.id`.

### CORS

Jika ada request cross-origin, pastikan CORS sudah dikonfigurasi di `app/main.py`. Saat ini sudah ada middleware CORS yang mengizinkan semua origin (`"*"`). Untuk produksi, ganti dengan domain spesifik:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://helpdeskit.biz.id", "https://www.helpdeskit.biz.id"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Cookie & Session

Jika menggunakan cookie authentication, pastikan `Secure` flag sudah di-set karena akses via HTTPS:

```python
# Di router/auth.py, pastikan cookie memiliki:
response.set_cookie(
    key="auth_token",
    value=token,
    httponly=True,
    secure=True,        # Wajib untuk HTTPS
    samesite="lax",
    max_age=3600,
)
```

## 🔍 Troubleshooting

### Domain masih mengarah ke IP lokal

Pastikan:
1. Nameserver domain sudah ke Cloudflare
2. Record DNS di Cloudflare sudah Proxied (oranye)
3. Tunnel sudah running (`cloudflared tunnel list`)

### 502 Bad Gateway

- Pastikan aplikasi Helpdesk sudah berjalan: `curl http://localhost:8000/api/health`
- Cek log tunnel: `sudo journalctl -u cloudflared@helpdeskit-tunnel -f`

### cloudflared tunnel login gagal

- Pastikan browser terbuka dan login berhasil
- Jika di server headless, gunakan: `cloudflared tunnel login --origins http://localhost:43437`

### Port sudah dipakai

Jika port 8000 sudah dipakai, ubah di `config.yml`:

```yaml
ingress:
  - hostname: helpdeskit.biz.id
    service: http://localhost:8080  # ganti port
```

## 📊 Monitoring

```bash
# Lihat semua tunnel
cloudflared tunnel list

# Lihat koneksi aktif
cloudflared tunnel connections

# Restart tunnel
sudo systemctl restart cloudflared@helpdeskit-tunnel

# Stop tunnel
sudo systemctl stop cloudflared@helpdeskit-tunnel
```

## 🔗 Referensi

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Cloudflare Tunnel Quick Start](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/tunnel-guide/)
- [Cloudflare Dashboard](https://dash.cloudflare.com/)
