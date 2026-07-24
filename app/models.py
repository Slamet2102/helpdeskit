from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="admin", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Unit(Base):
    __tablename__ = "unit"

    id = Column(Integer, primary_key=True, index=True)
    nama_unit = Column(String(100), unique=True, nullable=False)
    status = Column(String(20), default="Aktif", nullable=False)

    tiket = relationship("Tiket", back_populates="unit")


class JenisKerusakan(Base):
    __tablename__ = "jenis_kerusakan"

    id = Column(Integer, primary_key=True, index=True)
    kategori = Column(String(20), nullable=False)  # Hardware / Jaringan
    nama_kerusakan = Column(String(100), nullable=False)
    status = Column(String(20), default="Aktif", nullable=False)

    tiket = relationship("Tiket", back_populates="kerusakan")


class Tiket(Base):
    __tablename__ = "tiket"

    id = Column(Integer, primary_key=True, index=True)
    nomor_tiket = Column(String(30), unique=True, nullable=False, index=True)
    tanggal = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    nama_pelapor = Column(String(100), nullable=False)
    no_whatsapp = Column(String(20), nullable=False)
    unit_id = Column(Integer, ForeignKey("unit.id"), nullable=False)
    kerusakan_id = Column(Integer, ForeignKey("jenis_kerusakan.id"), nullable=False)
    deskripsi = Column(Text, nullable=True)
    foto = Column(String(255), nullable=True)
    status = Column(String(20), default="Open")  # Open, On Progress, Pending, Selesai, Batal, Rusak
    is_archived = Column(Boolean, default=False, nullable=False)
    durasi_menit = Column(Integer, nullable=True)
    durasi = Column(String(10), nullable=True)

    unit = relationship("Unit", back_populates="tiket")
    kerusakan = relationship("JenisKerusakan", back_populates="tiket")
    progress = relationship("Progress", back_populates="tiket", order_by="Progress.tanggal")


class Progress(Base):
    __tablename__ = "progress"

    id = Column(Integer, primary_key=True, index=True)
    tiket_id = Column(Integer, ForeignKey("tiket.id"), nullable=False)
    status = Column(String(20), nullable=False)
    catatan = Column(Text, nullable=True)
    waha_sent = Column(Boolean, server_default=text('0'), nullable=False)
    tanggal = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tiket = relationship("Tiket", back_populates="progress")

