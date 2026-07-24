from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Unit, JenisKerusakan, User
from ..schemas import (
    UnitSchema,
    JenisKerusakanSchema,
    UserSchema,
    UserCreateSchema,
    UserUpdateSchema,
    UnitUpdateSchema,
    JenisKerusakanUpdateSchema,
)

router = APIRouter(prefix="/api/master", tags=["Master Data"])


# ===== USER MANAGEMENT =====
@router.get("/users", response_model=List[UserSchema])
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()


@router.post("/users", response_model=UserSchema)
def create_user(data: UserCreateSchema, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username sudah digunakan")
    user = User(
        username=data.username,
        password_hash=data.password,
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserSchema)
def update_user(user_id: int, data: UserUpdateSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if data.username is not None:
        existing = db.query(User).filter(User.username == data.username, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username sudah digunakan")
        user.username = data.username
    if data.password is not None:
        user.password_hash = data.password
    if data.role is not None:
        user.role = data.role
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    db.delete(user)
    db.commit()
    return {"message": "User berhasil dihapus"}


# ===== UNIT =====
@router.get("/units", response_model=List[UnitSchema])
def get_units(db: Session = Depends(get_db)):
    return db.query(Unit).all()


@router.post("/units", response_model=UnitSchema)
def create_unit(nama_unit: str, status: str = Query("Aktif"), db: Session = Depends(get_db)):
    existing = db.query(Unit).filter(Unit.nama_unit == nama_unit).first()
    if existing:
        raise HTTPException(status_code=400, detail="Unit already exists")
    unit = Unit(nama_unit=nama_unit, status=status)
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


@router.put("/units/{unit_id}", response_model=UnitSchema)
def update_unit(unit_id: int, data: UnitUpdateSchema, db: Session = Depends(get_db)):
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit tidak ditemukan")
    if data.nama_unit is not None:
        unit.nama_unit = data.nama_unit
    if data.status is not None:
        unit.status = data.status
    db.commit()
    db.refresh(unit)
    return unit


@router.delete("/units/{unit_id}")
def delete_unit(unit_id: int, db: Session = Depends(get_db)):
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    db.delete(unit)
    db.commit()
    return {"message": "Unit deleted"}


# ===== JENIS KERUSAKAN =====
@router.get("/kerusakan", response_model=List[JenisKerusakanSchema])
def get_kerusakan(kategori: str = None, db: Session = Depends(get_db)):
    query = db.query(JenisKerusakan)
    if kategori:
        query = query.filter(JenisKerusakan.kategori == kategori)
    return query.all()


@router.post("/kerusakan", response_model=JenisKerusakanSchema)
def create_kerusakan(kategori: str, nama_kerusakan: str, status: str = Query("Aktif"), db: Session = Depends(get_db)):
    existing = db.query(JenisKerusakan).filter(
        JenisKerusakan.nama_kerusakan == nama_kerusakan
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Jenis kerusakan already exists")
    item = JenisKerusakan(kategori=kategori, nama_kerusakan=nama_kerusakan, status=status)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/kerusakan/{kerusakan_id}", response_model=JenisKerusakanSchema)
def update_kerusakan(kerusakan_id: int, data: JenisKerusakanUpdateSchema, db: Session = Depends(get_db)):
    item = db.query(JenisKerusakan).filter(JenisKerusakan.id == kerusakan_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Jenis kerusakan tidak ditemukan")
    if data.kategori is not None:
        item.kategori = data.kategori
    if data.nama_kerusakan is not None:
        item.nama_kerusakan = data.nama_kerusakan
    if data.status is not None:
        item.status = data.status
    db.commit()
    db.refresh(item)
    return item


@router.delete("/kerusakan/{kerusakan_id}")
def delete_kerusakan(kerusakan_id: int, db: Session = Depends(get_db)):
    item = db.query(JenisKerusakan).filter(JenisKerusakan.id == kerusakan_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Jenis kerusakan not found")
    db.delete(item)
    db.commit()
    return {"message": "Jenis kerusakan deleted"}

