import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import pytest

# Ensure project root is on sys.path so `app` package is importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    j = resp.json()
    assert j.get("status") == "ok"


def test_get_units():
    resp = client.get("/api/master/units")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


@patch("app.waha.notify_tiket_baru", new_callable=lambda: AsyncMock(return_value=True))
@patch("app.waha.notify_status_change", new_callable=lambda: AsyncMock(return_value=True))
def test_create_and_update_tiket(mock_notify_status, mock_notify_baru):
    # create tiket
    resp = client.post(
        "/api/tiket/",
        data={
            "nama_pelapor": "Test User",
            "no_whatsapp": "628199999999",
            "unit_id": 1,
            "kerusakan_id": 1,
            "deskripsi": "Tes otomatis"
        },
    )
    assert resp.status_code == 200
    tiket = resp.json()
    assert tiket.get("nomor_tiket")
    tid = tiket.get("id")

    # update status
    resp2 = client.put(f"/api/tiket/{tid}/status", json={"status": "On Progress", "catatan": "Mulai"})
    assert resp2.status_code == 200
    updated = resp2.json()
    assert updated.get("status") == "On Progress"
    # progress must have at least 2 entries (created + update)
    assert len(updated.get("progress", [])) >= 2


if __name__ == "__main__":
    pytest.main(["-q"])