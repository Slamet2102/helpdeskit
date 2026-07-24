#!/usr/bin/env python3
"""Simple migration script to add `waha_sent` column to `progress` table.

Idempotent: jika kolom sudah ada, skrip tidak melakukan perubahan.
"""
import os
import sys
import sqlite3
from pathlib import Path

# Ensure project root is on sys.path so `app` package can be imported when
# running this script directly.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import DATABASE_URL


def is_sqlite(url: str) -> bool:
    return url.startswith("sqlite:")


def sqlite_path(url: str) -> str:
    # supports sqlite:///relative/path or sqlite:////absolute/path
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "")
    if url.startswith("sqlite:////"):
        return url.replace("sqlite:////", "/")
    return url


def ensure_waha_sent(path: str) -> None:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(progress)")
        cols = [r[1] for r in cur.fetchall()]
        # Ensure waha_sent exists in progress
        if "waha_sent" in cols:
            print("Column 'waha_sent' already exists in progress table.")
        else:
            print("Adding column 'waha_sent' to progress table...")
            cur.execute("ALTER TABLE progress ADD COLUMN waha_sent INTEGER NOT NULL DEFAULT 0")
            conn.commit()
            print("Column added to progress.")

        # Also ensure tiket.durasi_menit exists
        try:
            cur.execute("PRAGMA table_info(tiket)")
            tiket_cols = [r[1] for r in cur.fetchall()]
            if "durasi_menit" in tiket_cols:
                print("Column 'durasi_menit' already exists in tiket table; nothing to do.")
            else:
                print("Adding column 'durasi_menit' to tiket table...")
                cur.execute("ALTER TABLE tiket ADD COLUMN durasi_menit INTEGER NULL")
                conn.commit()
                print("Column added to tiket.")
        except Exception:
            pass

        # Also add a human-readable durasi (HH:MM)
        try:
            cur.execute("PRAGMA table_info(tiket)")
            tiket_cols = [r[1] for r in cur.fetchall()]
            if "durasi" in tiket_cols:
                print("Column 'durasi' already exists in tiket table; nothing to do.")
            else:
                print("Adding column 'durasi' to tiket table...")
                cur.execute("ALTER TABLE tiket ADD COLUMN durasi TEXT NULL")
                conn.commit()
                print("Column 'durasi' added to tiket.")
        except Exception:
            pass
        except Exception:
            # best-effort; ignore if fails
            pass
    finally:
        cur.close()
        conn.close()


def main():
    url = os.getenv("DATABASE_URL", DATABASE_URL)
    if not is_sqlite(url):
        print("This migration script only supports SQLite DATABASE_URL.")
        return
    path = sqlite_path(url.replace("sqlite://", "sqlite://"))
    # normalize
    path = sqlite_path(url)
    print(f"Using SQLite DB: {path}")
    ensure_waha_sent(path)
    # Backfill human-readable durasi from durasi_menit or HH:MM values
    try:
        backfill_durasi(path)
    except Exception:
        pass


def backfill_durasi(path: str) -> None:
    """Fill `durasi` column using `durasi_menit` or convert HH:MM to full text."""
    import re

    conn = sqlite3.connect(path)
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, durasi_menit, durasi FROM tiket")
        rows = cur.fetchall()
        updated = 0
        for rid, dm, dtext in rows:
            new_text = None
            if dtext and isinstance(dtext, str):
                # if already in HH:MM form like '00:30' convert to full text
                if re.match(r"^\d{1,2}:\d{2}$", dtext):
                    parts = dtext.split(":")
                    try:
                        h = int(parts[0])
                        m = int(parts[1])
                        if h > 0 and m > 0:
                            new_text = f"{h} jam {m} menit"
                        elif h > 0:
                            new_text = f"{h} jam"
                        else:
                            new_text = f"{m} menit"
                    except Exception:
                        new_text = None
            if new_text is None and dm is not None:
                try:
                    h = int(dm) // 60
                    m = int(dm) % 60
                    if h > 0 and m > 0:
                        new_text = f"{h} jam {m} menit"
                    elif h > 0:
                        new_text = f"{h} jam"
                    else:
                        new_text = f"{m} menit"
                except Exception:
                    new_text = None

            if new_text and (not dtext or dtext != new_text):
                cur.execute("UPDATE tiket SET durasi = ? WHERE id = ?", (new_text, rid))
                updated += 1
        if updated:
            conn.commit()
            print(f"Backfilled durasi for {updated} tiket(s).")
        else:
            print("No tiket rows needed durasi backfill.")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
