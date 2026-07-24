@echo off
REM ========================================
REM  start.bat — Jalankan Helpdesk IT RS
REM  Untuk Windows (double-click)
REM ========================================

cd /d "%~dp0"
echo ========================================
echo   Helpdesk IT Rumah Sakit
echo   Starting all services...
echo ========================================

REM Cek Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak ditemukan. Install Python 3.11+ dulu.
    pause
    exit /b 1
)

REM Cek virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Membuat virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Gagal membuat virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
)

REM Aktifkan virtual environment
call .venv\Scripts\activate.bat

REM Install dependencies
echo [INFO] Memeriksa dependencies...
python -c "import uvicorn" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Menginstall dependencies...
    pip install --upgrade pip --quiet
    pip install fastapi uvicorn sqlalchemy jinja2 python-dotenv aiofiles httpx pydantic --quiet
    if %errorlevel% neq 0 (
        echo [ERROR] Gagal install dependencies.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed.
) else (
    echo [OK] Semua dependencies sudah tersedia.
)

echo.
echo ========================================
echo   Server siap dijalankan!
echo ========================================
echo   Local:    http://localhost:8000
echo   Docs API: http://localhost:8000/docs
echo ========================================
echo.
echo Tekan Ctrl+C untuk menghentikan server.
echo.

REM Jalankan server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause

