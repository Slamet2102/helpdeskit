import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import io

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app

client = TestClient(app)


@patch("app.waha.notify_tiket_baru", new_callable=lambda: AsyncMock(return_value=True))
@patch("app.waha.notify_status_change", new_callable=lambda: AsyncMock(return_value=True))
def test_file_upload_and_pagination(mock_notify_status, mock_notify_baru):
    # Upload a file with tiket
    file_content = b"dummy-image-bytes"
    files = {
        "foto": ("test.jpg", io.BytesIO(file_content), "image/jpeg")
    }
    data = {
        "nama_pelapor": "Uploader",
        "no_whatsapp": "628199000000",
        "unit_id": 1,
        "kerusakan_id": 1,
        "deskripsi": "Upload test"
    }
    resp = client.post("/api/tiket/", data=data, files=files)
    assert resp.status_code == 200
    tiket = resp.json()
    assert tiket.get("foto") is not None

    # Create additional tickets to test pagination
    for i in range(12):
        client.post(
            "/api/tiket/",
            data={
                "nama_pelapor": f"User{i}",
                "no_whatsapp": f"62810000000{i}",
                "unit_id": 1 if i % 2 == 0 else 2,
                "kerusakan_id": 1,
                "deskripsi": "bulk"
            },
        )

    # Page 2 with limit 5 should return 5 items
    resp2 = client.get("/api/tiket?limit=5&page=2")
    assert resp2.status_code == 200
    page_items = resp2.json()
    assert isinstance(page_items, list)
    assert len(page_items) == 5


def test_master_create_and_delete_unit():
    # create a new unit
    resp = client.post("/api/master/units", params={"nama_unit": "UnitTestX"})
    assert resp.status_code == 200
    unit = resp.json()
    assert unit.get("nama_unit") == "UnitTestX"
    uid = unit.get("id")

    # delete it
    resp2 = client.delete(f"/api/master/units/{uid}")
    assert resp2.status_code == 200
    j = resp2.json()
    assert j.get("message") == "Unit deleted"
