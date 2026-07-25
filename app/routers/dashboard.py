import io
import csv
import httpx
import logging
from fastapi import APIRouter, Depends, Query, Response, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fpdf import FPDF
from ..database import get_db
from ..models import Tiket, Unit, JenisKerusakan
from ..config import WAHA_API_URL, WAHA_API_KEY, WAHA_SESSION_NAME

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/waha-status")
async def check_waha_status():
    """Cek status koneksi WAHA."""
    result = {
        "connected": False,
        "session": WAHA_SESSION_NAME,
        "presence": "unknown",
        "error": None,
    }
    try:
        headers = {"Content-Type": "application/json", "X-Api-Key": WAHA_API_KEY} if WAHA_API_KEY else {"Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{WAHA_API_URL}/sessions",
                headers=headers,
            )
            if resp.status_code == 200:
                sessions = resp.json()
                for s in sessions:
                    if s.get("name") == WAHA_SESSION_NAME:
                        status = s.get("status", "UNKNOWN")
                        presence = s.get("presence", "unknown")
                        me = s.get("me", {})
                        result["connected"] = status == "WORKING" and presence == "online"
                        result["presence"] = presence
                        result["me"] = me.get("id") if me else None
                        result["status"] = status
                        break
                if not result.get("status"):
                    result["error"] = f"Session '{WAHA_SESSION_NAME}' not found"
            else:
                result["error"] = f"WAHA returned {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        result["error"] = str(e)[:200]
        logger.exception("Error checking WAHA status")
    return result


@router.get("/stats")
def get_dashboard_stats(
    today: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Mengembalikan statistik KPI dashboard berdasarkan data real ticket.
    
    - `total_hari_ini` SELALU dihitung dari tiket hari ini (tidak tergantung parameter `today`).
    - Jika `today=True`, maka stat Open/On Progress/Pending/Selesai ikut difilter berdasarkan hari ini.
    - Jika `today=False`, stat Open/On Progress/Pending/Selesai menampilkan total seluruh tiket.
    """
    local_tz = datetime.now().astimezone().tzinfo
    today_local = datetime.now(local_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    today_start = today_local.astimezone(timezone.utc)
    today_end = (today_local + timedelta(days=1)).astimezone(timezone.utc)

    # SELALU hitung jumlah tiket hari ini (tidak tergantung parameter `today`)
    today_count = db.query(func.count(Tiket.id)).filter(
        Tiket.tanggal >= today_start,
        Tiket.tanggal < today_end,
        Tiket.is_archived == False
    ).scalar()

    # Base query untuk status counts, opsional difilter hari ini
    base_query = db.query(Tiket).filter(Tiket.is_archived == False)
    if today:
        base_query = base_query.filter(Tiket.tanggal >= today_start, Tiket.tanggal < today_end)

    open_count = base_query.filter(Tiket.status == "Open").count()
    on_progress = base_query.filter(Tiket.status == "On Progress").count()
    pending = base_query.filter(Tiket.status == "Pending").count()
    selesai = base_query.filter(Tiket.status == "Selesai").count()

    # Total semua tiket (tidak termasuk arsip) — tidak terpengaruh parameter today
    total_all = db.query(func.count(Tiket.id)).filter(Tiket.is_archived == False).scalar()

    return {
        "total_hari_ini": today_count or 0,
        "total_all": total_all or 0,
        "open": open_count or 0,
        "on_progress": on_progress or 0,
        "pending": pending or 0,
        "selesai": selesai or 0,
    }


@router.get("/daily-summary")
def get_daily_summary(days: int = Query(7, ge=1, le=30), db: Session = Depends(get_db)):
    """Mengembalikan ringkasan tiket harian untuk chart di dashboard."""
    local_tz = datetime.now().astimezone().tzinfo
    today_local = datetime.now(local_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    start_local = today_local - timedelta(days=days - 1)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = (today_local + timedelta(days=1)).astimezone(timezone.utc)

    tickets = db.query(Tiket).filter(
        Tiket.tanggal >= start_utc,
        Tiket.tanggal < end_utc,
        Tiket.is_archived == False,
    ).all()

    date_counts = {}
    current = start_local
    for _ in range(days):
        date_key = current.strftime("%Y-%m-%d")
        date_counts[date_key] = 0
        current += timedelta(days=1)

    for ticket in tickets:
        if ticket.tanggal is None:
            continue
        try:
            ticket_local = ticket.tanggal.astimezone(local_tz)
        except Exception:
            ticket_local = ticket.tanggal.replace(tzinfo=local_tz)

        ticket_key = ticket_local.strftime("%Y-%m-%d")
        if ticket_key in date_counts:
            date_counts[ticket_key] += 1

    series = []
    for offset in range(days):
        day = start_local + timedelta(days=offset)
        key = day.strftime("%Y-%m-%d")
        series.append({
            "date": key,
            "count": date_counts.get(key, 0),
        })

    return {
        "series": series,
        "total": sum(item["count"] for item in series),
    }


@router.get("/tiket")
def get_tiket_period(
    year: int = Query(None),
    month: int = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
):
    """Ambil tiket untuk periode tertentu. Jika `month` kosong, ambil seluruh tahun."""
    local_tz = datetime.now().astimezone().tzinfo
    if year is None and month is None:
        now = datetime.now(local_tz)
        year = now.year
        month = now.month

    if year is not None and month is not None:
        start_local = datetime(year, month, 1, tzinfo=local_tz)
        if month == 12:
            end_local = datetime(year + 1, 1, 1, tzinfo=local_tz)
        else:
            end_local = datetime(year, month + 1, 1, tzinfo=local_tz)
    else:
        start_local = datetime(year, 1, 1, tzinfo=local_tz)
        end_local = datetime(year + 1, 1, 1, tzinfo=local_tz)

    start = start_local.astimezone(ZoneInfo("UTC"))
    end = end_local.astimezone(ZoneInfo("UTC"))

    query = db.query(Tiket).filter(Tiket.tanggal >= start, Tiket.tanggal < end, Tiket.is_archived == False).order_by(Tiket.tanggal.asc())
    results = []
    for t in query.all():
        tanggal_local = t.tanggal
        if tanggal_local is not None:
            try:
                tanggal_local = tanggal_local.astimezone(local_tz)
            except Exception:
                tanggal_local = tanggal_local.replace(tzinfo=local_tz)
        results.append(
            {
                "id": t.id,
                "nomor_tiket": t.nomor_tiket,
                "tanggal": tanggal_local.isoformat() if tanggal_local is not None else None,
                "nama_pelapor": t.nama_pelapor,
                "no_whatsapp": t.no_whatsapp,
                "unit": t.unit.nama_unit if t.unit else None,
                "kerusakan": t.kerusakan.nama_kerusakan if t.kerusakan else None,
                "kategori": t.kerusakan.kategori if t.kerusakan else None,
                "deskripsi": t.deskripsi,
                "status": t.status,
                "durasi": t.durasi,
                "durasi_menit": t.durasi_menit,
            }
        )

    return results


@router.post("/import")
def import_tiket_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Import tiket dari file CSV."""
    if file.content_type not in ["text/csv", "application/vnd.ms-excel", "text/plain"]:
        raise HTTPException(status_code=400, detail="File harus berformat CSV")

    text_data = file.file.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text_data))
    imported = []
    for row in reader:
        nama_pelapor = row.get('nama_pelapor') or row.get('nama')
        no_whatsapp = row.get('no_whatsapp') or row.get('whatsapp')
        unit_key = row.get('unit')
        kerusakan_key = row.get('kerusakan')
        deskripsi = row.get('deskripsi') or row.get('description')
        status = row.get('status') or 'Open'
        tanggal_str = row.get('tanggal')
        if not nama_pelapor or not no_whatsapp or not unit_key or not kerusakan_key:
            continue

        import re
        digits = re.sub(r"\D", "", no_whatsapp)
        if digits.startswith('0'):
            digits = '62' + digits[1:]
        elif digits.startswith('8'):
            digits = '62' + digits
        no_whatsapp = digits

        unit = None
        if unit_key.isdigit():
            unit = db.query(Unit).filter(Unit.id == int(unit_key)).first()
        if not unit:
            unit = db.query(Unit).filter(Unit.nama_unit == unit_key).first()
        if not unit:
            continue

        kerusakan = None
        if kerusakan_key.isdigit():
            kerusakan = db.query(JenisKerusakan).filter(JenisKerusakan.id == int(kerusakan_key)).first()
        if not kerusakan:
            kerusakan = db.query(JenisKerusakan).filter(JenisKerusakan.nama_kerusakan == kerusakan_key).first()
        if not kerusakan:
            continue

        if status not in ['Open', 'On Progress', 'Pending', 'Selesai', 'Batal', 'Rusak']:
            status = 'Open'

        if tanggal_str:
            try:
                tanggal = datetime.fromisoformat(tanggal_str)
                if tanggal.tzinfo is None:
                    tanggal = tanggal.replace(tzinfo=timezone.utc)
            except Exception:
                tanggal = datetime.now(timezone.utc)
        else:
            tanggal = datetime.now(timezone.utc)

        nomor_tiket = row.get('nomor_tiket') or row.get('ticket_number')
        if not nomor_tiket:
            base = datetime.now().strftime('%Y%m%d')
            nomor_tiket = f"IT-{base}-"
            counter = 1
            while True:
                candidate = f"{nomor_tiket}{counter:03d}"
                if not db.query(Tiket).filter(Tiket.nomor_tiket == candidate).first():
                    nomor_tiket = candidate
                    break
                counter += 1

        tiket = Tiket(
            nomor_tiket=nomor_tiket,
            nama_pelapor=nama_pelapor,
            no_whatsapp=no_whatsapp,
            unit_id=unit.id,
            kerusakan_id=kerusakan.id,
            deskripsi=deskripsi,
            status=status,
            tanggal=tanggal,
        )
        db.add(tiket)
        imported.append(nomor_tiket)

    db.commit()
    return {"imported": imported, "count": len(imported)}


class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "Laporan Tiket Helpdesk IT", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Halaman {self.page_no()}/{{nb}}", align="C")


def generate_pdf(data: list) -> bytes:
    """Generate PDF dari data tiket."""
    pdf = PDF(orientation="L", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 9)

    # Column widths (landscape A4 = 297mm width, with margins ~277mm usable)
    col_widths = [8, 25, 28, 35, 28, 28, 28, 22, 40, 18, 12, 12]
    headers = [
        "No", "No Tiket", "Tanggal", "Pelapor", "No WA",
        "Unit", "Kerusakan", "Kategori", "Deskripsi", "Status",
        "Durasi", "Menit"
    ]

    # Header row
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, align="C")
    pdf.ln()

    # Data rows
    pdf.set_font("Helvetica", "", 7)
    for idx, r in enumerate(data, start=1):
        row_data = [
            str(idx),
            r.get("nomor_tiket", ""),
            r.get("tanggal", "")[:10] if r.get("tanggal") else "",
            r.get("nama_pelapor", ""),
            r.get("no_whatsapp", ""),
            r.get("unit", ""),
            r.get("kerusakan", ""),
            r.get("kategori", ""),
            r.get("deskripsi", "")[:40],
            r.get("status", ""),
            r.get("durasi", ""),
            str(r.get("durasi_menit", "") or ""),
        ]
        for i, val in enumerate(row_data):
            pdf.cell(col_widths[i], 6, val, border=1, align="C" if i == 0 else "L")
        pdf.ln()

    return pdf.output()


@router.get("/export")
def export_tiket_period(
    year: int = Query(None),
    month: int = Query(None, ge=1, le=12),
    format: str = Query("csv"),
    db: Session = Depends(get_db),
):
    """Export tiket untuk periode sebagai CSV (default) atau PDF."""
    data = get_tiket_period(year=year, month=month, db=db)

    if format == "pdf":
        pdf_bytes = generate_pdf(data)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=tiket_export.pdf"}
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "nomor_tiket", "tanggal", "nama_pelapor", "no_whatsapp",
        "unit", "kerusakan", "kategori", "deskripsi", "status",
        "durasi", "durasi_menit"
    ])
    for r in data:
        writer.writerow([
            r["id"], r["nomor_tiket"], r["tanggal"], r["nama_pelapor"],
            r["no_whatsapp"], r["unit"], r["kerusakan"], r.get("kategori", ""),
            r.get("deskripsi", ""), r["status"], r["durasi"], r.get("durasi_menit", "")
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tiket_export.csv"}
    )
