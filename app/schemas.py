from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone


def serialize_local_datetime(dt: datetime) -> str:
    if dt is None:
        return None
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local_tz = datetime.now().astimezone().tzinfo
        return dt.astimezone(local_tz).isoformat()
    except Exception:
        return dt.isoformat()


class UserSchema(BaseModel):
    id: int
    username: str
    role: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: serialize_local_datetime,
        }


class UserCreateSchema(BaseModel):
    username: str
    password: str
    role: str = "admin"


class UserUpdateSchema(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None


class UnitUpdateSchema(BaseModel):
    nama_unit: Optional[str] = None
    status: Optional[str] = None


class JenisKerusakanUpdateSchema(BaseModel):
    kategori: Optional[str] = None
    nama_kerusakan: Optional[str] = None
    status: Optional[str] = None


class UnitSchema(BaseModel):
    id: int
    nama_unit: str
    status: str

    class Config:
        from_attributes = True


class JenisKerusakanSchema(BaseModel):
    id: int
    kategori: str
    nama_kerusakan: str
    status: str

    class Config:
        from_attributes = True


class ProgressSchema(BaseModel):
    id: int
    status: str
    catatan: Optional[str] = None
    waha_sent: Optional[bool] = False
    tanggal: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: serialize_local_datetime,
        }


class TiketCreate(BaseModel):
    nama_pelapor: str
    no_whatsapp: str
    unit_id: int
    kerusakan_id: int
    deskripsi: Optional[str] = None


class TiketUpdateStatus(BaseModel):
    status: str
    catatan: Optional[str] = None


class TiketResponse(BaseModel):
    id: int
    nomor_tiket: str
    tanggal: datetime
    nama_pelapor: str
    no_whatsapp: str
    unit_id: int
    kerusakan_id: int
    deskripsi: Optional[str] = None
    foto: Optional[str] = None
    status: str
    durasi_menit: Optional[int] = None
    durasi: Optional[str] = None
    unit: Optional[UnitSchema] = None
    kerusakan: Optional[JenisKerusakanSchema] = None
    is_archived: bool = False
    progress: List[ProgressSchema] = []

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: serialize_local_datetime,
        }


class DashboardResponse(BaseModel):
    total_hari_ini: int
    open: int
    on_progress: int
    pending: int
    selesai: int

