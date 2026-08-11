#!/bin/bash

# Pindah ke direktori tempat script ini berada (mencegah error jika dijalankan dari luar folder)
# cd "$(dirname "$0")"

# Cek apakah folder .venv ada
if [ -d ".venv" ]; then
    echo "Mengaktifkan virtual environment..."
    source .venv/bin/activate
else
    echo "Peringatan: Folder .venv tidak ditemukan!"
fi

# Jalankan aplikasi (Di Ubuntu, gunakan python3)
echo "Menjalankan app.py..."
python3 app.py

# Nonaktifkan venv setelah aplikasi ditutup (Ctrl+C)
deactivate