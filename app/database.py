from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
from .config import DATABASE_URL
from sqlalchemy import inspect, text

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency untuk mendapatkan database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def has_column(table_name: str, column_name: str) -> bool:
    try:
        inspector = inspect(engine)
        cols = [c["name"] for c in inspector.get_columns(table_name)]
        return column_name in cols
    except Exception:
        return False


def init_db():
    """Inisialisasi database dan buat semua tabel."""
    from .models import User, Unit, JenisKerusakan  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Ensure new column waha_sent exists in progress table for backward compatibility
    try:
        inspector = inspect(engine)
        cols = [c["name"] for c in inspector.get_columns("progress")]
        if "waha_sent" not in cols:
            try:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE progress ADD COLUMN waha_sent INTEGER NOT NULL DEFAULT 0"))
            except Exception:
                try:
                    rc = engine.raw_connection()
                    cur = rc.cursor()
                    cur.execute("ALTER TABLE progress ADD COLUMN waha_sent INTEGER NOT NULL DEFAULT 0")
                    rc.commit()
                    cur.close()
                    rc.close()
                except Exception:
                    pass
    except Exception:
        pass
    try:
        if DATABASE_URL.startswith("sqlite"):
            import sqlite3 as _sqlite
            path = DATABASE_URL.replace("sqlite:///", "")
            conn = _sqlite.connect(path)
            cur = conn.cursor()
            try:
                cur.execute("ALTER TABLE progress ADD COLUMN waha_sent INTEGER NOT NULL DEFAULT 0")
                conn.commit()
            except Exception:
                pass
            finally:
                cur.close()
                conn.close()
    except Exception:
        pass

    try:
        if DATABASE_URL.startswith("sqlite"):
            import sqlite3 as _sqlite
            path = DATABASE_URL.replace("sqlite:///", "")
            conn = _sqlite.connect(path)
            cur = conn.cursor()
            try:
                cur.execute("ALTER TABLE tiket ADD COLUMN is_archived INTEGER NOT NULL DEFAULT 0")
                conn.commit()
            except Exception:
                pass
            finally:
                cur.close()
                conn.close()
    except Exception:
        pass

    # Ensure optional status column exists for master data
    try:
        inspector2 = inspect(engine)
        cols = [c["name"] for c in inspector2.get_columns("unit")]
        if "status" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE unit ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'Aktif'"))
    except Exception:
        pass
    try:
        inspector3 = inspect(engine)
        cols = [c["name"] for c in inspector3.get_columns("jenis_kerusakan")]
        if "status" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE jenis_kerusakan ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'Aktif'"))
    except Exception:
        pass
    try:
        inspector4 = inspect(engine)
        cols = [c["name"] for c in inspector4.get_columns("tiket")]
        if "is_archived" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE tiket ADD COLUMN is_archived INTEGER NOT NULL DEFAULT 0"))
    except Exception:
        pass

    # Seed admin user if not exists (plain text password)
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin = User(
                username="admin",
                password_hash="admin",
                role="admin",
            )
            db.add(admin)
            db.commit()
            print("[DB] Admin user created: admin")
    except Exception as e:
        print(f"[DB] Error seeding admin user: {e}")
    finally:
        db.close()

    # Seed data if tables are empty
    db = SessionLocal()
    try:
        try:
            if db.query(Unit).count() == 0:
                units = [
                    "IGD", "ICU", "Laboratorium", "Radiologi",
                    "Farmasi", "Rawat Inap", "Poli Umum", "Kasir",
                    "Ruang Server", "Administrasi"
                ]
                for u in units:
                    db.add(Unit(nama_unit=u))
                db.commit()
        except OperationalError:
            pass

        try:
            if db.query(JenisKerusakan).count() == 0:
                hardware = [
                    "PC Tidak Menyala", "PC Lambat", "Monitor Rusak",
                    "Printer Tidak Bisa Print", "Scanner Bermasalah",
                    "Keyboard Rusak", "Mouse Rusak", "UPS Bermasalah"
                ]
                jaringan = [
                    "Internet Putus", "WiFi Tidak Tersambung", "LAN Tidak Berfungsi",
                    "Tidak Bisa Akses SIMRS", "Server Tidak Bisa Diakses",
                    "Switch Bermasalah", "Access Point Mati", "IP Conflict"
                ]
                for h in hardware:
                    db.add(JenisKerusakan(kategori="Hardware", nama_kerusakan=h))
                for j in jaringan:
                    db.add(JenisKerusakan(kategori="Jaringan", nama_kerusakan=j))
                db.commit()
        except OperationalError:
            pass
    finally:
        db.close()
