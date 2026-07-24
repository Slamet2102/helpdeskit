import os
import shutil
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from ..database import get_db, has_column
from ..models import Tiket, Progress, Unit, JenisKerusakan
from ..schemas import TiketCreate, TiketUpdateStatus, TiketResponse
from ..config import UPLOAD_DIR, WAHA_IT_NUMBER
from ..events import event_manager
from ..waha import (
    notify_tiket_baru,
    notify_tiket_created_to_pelapor,
    notify_status_change,
    notify_status_to_it,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tiket", tags=["Tiket"])


class BatchDeleteRequest(BaseModel):
    ids: List[int]


def generate_nomor_tiket():
    """Generate nomor tiket: IT-YYYYMMDD-XXX"""
    now = datetime.now().astimezone()
    date_part = now.strftime("%Y%m%d")
    return f"IT-{date_part}-"


@router.post("/", response_model=TiketResponse)
async def create_tiket(
    nama_pelapor: str = Form(...),
    no_whatsapp: str = Form(...),
    unit_id: int = Form(...),
    kerusakan_id: int = Form(...),
    deskripsi: Optional[str] = Form(None),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Buat tiket baru."""
    import re
    raw_no = no_whatsapp.strip()
    digits = re.sub(r"\D", "", raw_no)
    if digits.startswith('0'):
        digits = '62' + digits[1:]
    elif digits.startswith('8'):
        digits = '62' + digits
    no_whatsapp = digits
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    kerusakan = db.query(JenisKerusakan).filter(JenisKerusakan.id == kerusakan_id).first()
    if not kerusakan:
        raise HTTPException(status_code=404, detail="Jenis kerusakan not found")

    prefix = generate_nomor_tiket()
    counter = 1
    while True:
        nomor_tiket = f"{prefix}{counter:03d}"
        existing = db.query(Tiket).filter(Tiket.nomor_tiket == nomor_tiket).first()
        if not existing:
            break
        counter += 1

    foto_path = None
    if foto and foto.filename:
        ext = os.path.splitext(foto.filename)[1] or ".jpg"
        filename = f"{nomor_tiket}{ext}"
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as f:
            shutil.copyfileobj(foto.file, f)
        foto_path = f"/uploads/{filename}"

    tiket = Tiket(
        nomor_tiket=nomor_tiket,
        nama_pelapor=nama_pelapor,
        no_whatsapp=no_whatsapp,
        unit_id=unit_id,
        kerusakan_id=kerusakan_id,
        deskripsi=deskripsi,
        foto=foto_path,
        status="Open",
        tanggal=datetime.now(timezone.utc)
    )
    db.add(tiket)
    db.commit()
    db.refresh(tiket)

    from sqlalchemy import text
    if has_column('progress', 'waha_sent'):
        db.execute(
            text(
                "INSERT INTO progress (tiket_id, status, catatan, waha_sent, tanggal) VALUES (:tiket_id, :status, :catatan, :waha_sent, :tanggal)"
            ),
            {
                "tiket_id": tiket.id,
                "status": "Open",
                "catatan": "Tiket dibuat",
                "waha_sent": 0,
                "tanggal": tiket.tanggal,
            },
        )
    else:
        db.execute(
            text(
                "INSERT INTO progress (tiket_id, status, catatan, tanggal) VALUES (:tiket_id, :status, :catatan, :tanggal)"
            ),
            {
                "tiket_id": tiket.id,
                "status": "Open",
                "catatan": "Tiket dibuat",
                "tanggal": tiket.tanggal,
            },
        )
    db.commit()

    sent_to_user = False
    try:
        sent_to_user = await notify_tiket_created_to_pelapor(
            no_whatsapp=tiket.no_whatsapp,
            nomor_tiket=tiket.nomor_tiket,
            nama_pelapor=tiket.nama_pelapor,
            ruangan=unit.nama_unit,
            kerusakan=kerusakan.nama_kerusakan,
            deskripsi=tiket.deskripsi or "",
        )
    except Exception as e:
        logger.exception("Error when sending WAHA ticket confirmation to user: %s", e)
        sent_to_user = False

    sent_to_group = False
    try:
        sent_to_group = await notify_tiket_baru(
            nomor_tiket=tiket.nomor_tiket,
            nama_pelapor=tiket.nama_pelapor,
            ruangan=unit.nama_unit,
            kerusakan=kerusakan.nama_kerusakan,
            deskripsi=tiket.deskripsi or "",
        )
    except Exception as e:
        logger.exception("Error when sending WAHA ticket notification to group/IT: %s", e)
        sent_to_group = False

    note = (
        f"Notifikasi WAHA ke user: {'Berhasil' if sent_to_user else 'Gagal'} | "
        f"Notifikasi WAHA ke group/IT: {'Berhasil' if sent_to_group else 'Gagal'}"
    )
    from sqlalchemy import text
    if has_column('progress', 'waha_sent'):
        db.execute(
            text(
                "INSERT INTO progress (tiket_id, status, catatan, waha_sent, tanggal) VALUES (:tiket_id, :status, :catatan, :waha_sent, :tanggal)"
            ),
            {
                "tiket_id": tiket.id,
                "status": "Open",
                "catatan": note,
                "waha_sent": 1 if (sent_to_user or sent_to_group) else 0,
                "tanggal": tiket.tanggal,
            },
        )
    else:
        db.execute(
            text(
                "INSERT INTO progress (tiket_id, status, catatan, tanggal) VALUES (:tiket_id, :status, :catatan, :tanggal)"
            ),
            {
                "tiket_id": tiket.id,
                "status": "Open",
                "catatan": note,
                "tanggal": tiket.tanggal,
            },
        )
    db.commit()

    db.refresh(tiket)

    # Broadcast real-time event for new ticket
    import asyncio
    asyncio.ensure_future(event_manager.broadcast("tiket_baru", {
        "id": tiket.id,
        "nomor_tiket": tiket.nomor_tiket,
        "nama_pelapor": tiket.nama_pelapor,
        "status": tiket.status,
        "unit": unit.nama_unit if unit else None,
        "kerusakan": kerusakan.nama_kerusakan if kerusakan else None,
    }))

    return tiket


@router.get("/", response_model=List[TiketResponse])
def get_tiket_list(
    response: Response,
    status: Optional[str] = Query(None),
    unit_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    today: bool = Query(False),
    sort_by: str = Query("tanggal"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Dapatkan daftar tiket dengan filter, sort, dan pagination."""
    query = db.query(Tiket).filter(Tiket.is_archived == False)

    if status:
        query = query.filter(Tiket.status == status)
    if unit_id:
        query = query.filter(Tiket.unit_id == unit_id)
    if search:
        query = query.filter(
            Tiket.nomor_tiket.contains(search) |
            Tiket.nama_pelapor.contains(search)
        )

    if today:
        local_tz = datetime.now().astimezone().tzinfo
        today_start_local = datetime.now(local_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end_local = today_start_local + timedelta(days=1)
        today_start_utc = today_start_local.astimezone(timezone.utc)
        today_end_utc = today_end_local.astimezone(timezone.utc)
        query = query.filter(Tiket.tanggal >= today_start_utc, Tiket.tanggal < today_end_utc)

    # Sorting
    sort_column = getattr(Tiket, sort_by, None)
    if sort_column is None:
        sort_column = Tiket.tanggal
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    total = query.count()
    total_pages = (total + limit - 1) // limit if total else 1
    tiket_list = query.offset((page - 1) * limit).limit(limit).all()

    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Total-Pages"] = str(total_pages)
    response.headers["X-Current-Page"] = str(page)

    return tiket_list


@router.get("/archive")
def get_archived_tiket(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Ambil daftar tiket yang sudah diarsipkan dengan pagination."""
    query = db.query(Tiket).filter(Tiket.is_archived == True)
    if search:
        query = query.filter(
            Tiket.nomor_tiket.contains(search) |
            Tiket.nama_pelapor.contains(search)
        )
    total = query.count()
    tiket_list = query.order_by(Tiket.tanggal.desc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "data": tiket_list,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit
    }


@router.post("/archive/{tiket_id}/restore", response_model=TiketResponse)
def restore_archived_tiket(tiket_id: int, db: Session = Depends(get_db)):
    """Pulihkan tiket dari arsip."""
    tiket = db.query(Tiket).filter(Tiket.id == tiket_id, Tiket.is_archived == True).first()
    if not tiket:
        raise HTTPException(status_code=404, detail="Archived ticket not found")
    tiket.is_archived = False
    db.add(tiket)
    db.commit()
    db.refresh(tiket)
    return tiket


@router.delete("/archive", response_model=dict)
def delete_archived_tiket(db: Session = Depends(get_db)):
    """Hapus permanen semua tiket di arsip."""
    archived = db.query(Tiket).filter(Tiket.is_archived == True).all()
    deleted_count = len(archived)
    for tiket in archived:
        # Hapus data progress terkait terlebih dahulu
        db.query(Progress).filter(Progress.tiket_id == tiket.id).delete()
        db.delete(tiket)
    db.commit()
    return {"deleted": deleted_count}


@router.delete("/archive/batch", response_model=dict)
def delete_archived_tiket_batch(req: BatchDeleteRequest, db: Session = Depends(get_db)):
    """Hapus permanen tiket arsip terpilih berdasarkan ID."""
    archived = db.query(Tiket).filter(Tiket.id.in_(req.ids), Tiket.is_archived == True).all()
    deleted_count = len(archived)
    for tiket in archived:
        # Hapus data progress terkait terlebih dahulu
        db.query(Progress).filter(Progress.tiket_id == tiket.id).delete()
        db.delete(tiket)
    db.commit()
    return {"deleted": deleted_count}


@router.get("/{tiket_id}", response_model=TiketResponse)
def get_tiket_detail(tiket_id: int, db: Session = Depends(get_db)):
    """Dapatkan detail tiket."""
    tiket = db.query(Tiket).filter(Tiket.id == tiket_id).first()
    if not tiket:
        raise HTTPException(status_code=404, detail="Tiket not found")
    return tiket


@router.put("/{tiket_id}/status", response_model=TiketResponse)
async def update_tiket_status(
    tiket_id: int,
    status_data: TiketUpdateStatus,
    db: Session = Depends(get_db),
):
    """Update status tiket dan kirim notifikasi."""
    tiket = db.query(Tiket).filter(Tiket.id == tiket_id).first()
    if not tiket:
        raise HTTPException(status_code=404, detail="Tiket not found")
    if tiket.is_archived:
        raise HTTPException(status_code=400, detail="Archived tiket tidak bisa diubah statusnya")
    if tiket.status == "Selesai":
        raise HTTPException(status_code=400, detail="Tiket selesai tidak bisa diubah statusnya")

    old_status = tiket.status
    tiket.status = status_data.status

    from sqlalchemy import text
    db.execute(
        text(
            "INSERT INTO progress (tiket_id, status, catatan, tanggal) VALUES (:tiket_id, :status, :catatan, :tanggal)"
        ),
        {
            "tiket_id": tiket.id,
            "status": status_data.status,
            "catatan": status_data.catatan,
            "tanggal": tiket.tanggal,
        },
    )
    db.commit()
    db.refresh(tiket)

    # Broadcast real-time event for status update
    import asyncio
    asyncio.ensure_future(event_manager.broadcast("status_update", {
        "id": tiket.id,
        "nomor_tiket": tiket.nomor_tiket,
        "status_lama": old_status,
        "status_baru": tiket.status,
    }))

    if old_status != status_data.status:
        durasi_text = None

        try:
            if status_data.status == "On Progress":
                try:
                    from datetime import datetime, timezone
                    now_time = datetime.now(timezone.utc)
                    created_time = tiket.tanggal
                    if created_time.tzinfo is None:
                        created_time = created_time.replace(tzinfo=timezone.utc)
                    durasi_min = int((now_time - created_time).total_seconds() / 60)
                    tiket.durasi_menit = durasi_min
                    h = durasi_min // 60
                    m = durasi_min % 60
                    if h > 0 and m > 0:
                        durasi_text = f"{h} jam {m} menit"
                    elif h > 0:
                        durasi_text = f"{h} jam"
                    else:
                        durasi_text = f"{m} menit"
                    tiket.durasi = durasi_text
                    db.add(tiket)
                    db.commit()
                    db.refresh(tiket)
                except Exception:
                    logger.exception("Gagal menghitung/menyimpan durasi saat On Progress")

            sent = await notify_status_change(
                no_whatsapp=tiket.no_whatsapp,
                nomor_tiket=tiket.nomor_tiket,
                status=status_data.status,
                nama_pelapor=tiket.nama_pelapor,
                ruangan=(tiket.unit.nama_unit if getattr(tiket, 'unit', None) else None),
                kerusakan=(tiket.kerusakan.nama_kerusakan if getattr(tiket, 'kerusakan', None) else None),
                deskripsi=tiket.deskripsi,
                durasi=durasi_text,
            )
        except Exception as e:
            logger.exception("Error when sending WAHA status notification: %s", e)
            sent = False

        note = f"Notifikasi status ke pelapor: {'Berhasil' if sent else 'Gagal'}"

        sent_it = False
        if status_data.status == "Selesai":
            try:
                sent_it = await notify_status_to_it(
                    nomor_tiket=tiket.nomor_tiket,
                    status=status_data.status,
                    to_number=WAHA_IT_NUMBER,
                    nama_pelapor=tiket.nama_pelapor,
                    ruangan=(tiket.unit.nama_unit if getattr(tiket, 'unit', None) else None),
                    kerusakan=(tiket.kerusakan.nama_kerusakan if getattr(tiket, 'kerusakan', None) else None),
                    deskripsi=tiket.deskripsi,
                    tanggal=str(tiket.tanggal),
                    durasi=tiket.durasi,
                )
            except Exception as e:
                logger.exception("Error when sending WAHA status to IT: %s", e)
                sent_it = False

        from sqlalchemy import text
        if has_column('progress', 'waha_sent'):
            db.execute(
                text(
                    "INSERT INTO progress (tiket_id, status, catatan, waha_sent, tanggal) VALUES (:tiket_id, :status, :catatan, :waha_sent, :tanggal)"
                ),
                {
                    "tiket_id": tiket.id,
                    "status": status_data.status,
                    "catatan": note,
                    "waha_sent": 1 if sent else 0,
                    "tanggal": tiket.tanggal,
                },
            )
        else:
            db.execute(
                text(
                    "INSERT INTO progress (tiket_id, status, catatan, tanggal) VALUES (:tiket_id, :status, :catatan, :tanggal)"
                ),
                {
                    "tiket_id": tiket.id,
                    "status": status_data.status,
                    "catatan": note,
                    "tanggal": tiket.tanggal,
                },
            )
        db.commit()

        if status_data.status == "Selesai":
            note_it = f"Notifikasi status ke IT: {'Berhasil' if sent_it else 'Gagal'}"
            if has_column('progress', 'waha_sent'):
                db.execute(
                    text(
                        "INSERT INTO progress (tiket_id, status, catatan, waha_sent, tanggal) VALUES (:tiket_id, :status, :catatan, :waha_sent, :tanggal)"
                    ),
                    {
                        "tiket_id": tiket.id,
                        "status": status_data.status,
                        "catatan": note_it,
                        "waha_sent": 1 if sent_it else 0,
                        "tanggal": tiket.tanggal,
                    },
                )
            else:
                db.execute(
                    text(
                        "INSERT INTO progress (tiket_id, status, catatan, tanggal) VALUES (:tiket_id, :status, :catatan, :tanggal)"
                    ),
                    {
                        "tiket_id": tiket.id,
                        "status": status_data.status,
                        "catatan": note_it,
                        "tanggal": tiket.tanggal,
                    },
                )
            db.commit()

    return tiket


@router.delete("/{tiket_id}", response_model=TiketResponse)
def archive_tiket(tiket_id: int, db: Session = Depends(get_db)):
    """Pindahkan tiket ke arsip (soft delete)."""
    tiket = db.query(Tiket).filter(Tiket.id == tiket_id, Tiket.is_archived == False).first()
    if not tiket:
        raise HTTPException(status_code=404, detail="Tiket not found or already archived")
    tiket.is_archived = True
    db.add(tiket)
    db.commit()
    db.refresh(tiket)
    return tiket
