import httpx
import logging
from typing import Optional
from .config import (
    WAHA_API_URL,
    WAHA_SESSION_NAME,
    WAHA_GROUP_ID,
    WAHA_API_KEY,
    WAHA_API_AUTH_HEADER_NAME,
    WAHA_API_KEY_IN,
    WAHA_API_KEY_PARAM,
    WAHA_IT_NUMBER,
    BASE_URL,
)

logger = logging.getLogger(__name__)

# Timeout lebih panjang untuk WAHA yang mungkin lambat memproses pesan WhatsApp
WAHA_TIMEOUT = 90


def _normalize_whatsapp_number(to: str) -> str:
    """Normalisasi nomor WhatsApp agar WAHA menerima format internasional yang konsisten."""
    if not to:
        return ""
    digits = ''.join(ch for ch in str(to) if ch.isdigit())
    if not digits:
        return str(to).strip()
    if digits.startswith('0'):
        digits = '62' + digits[1:]
    elif digits.startswith('8'):
        digits = '62' + digits
    return digits


def _ensure_chat_id(to: str) -> str:
    """Pastikan nomor memiliki suffix @c.us untuk WAHA."""
    to = _normalize_whatsapp_number(to).strip()
    if not to:
        return to
    if not to.endswith("@g.us") and not to.endswith("@c.us"):
        if "@" not in to:
            to = to + "@c.us"
    return to


def _get_headers() -> dict:
    """Buat headers dengan API key sesuai konfigurasi."""
    headers = {"Content-Type": "application/json"}
    if WAHA_API_KEY:
        if WAHA_API_KEY_IN == "header" and WAHA_API_AUTH_HEADER_NAME:
            headers[WAHA_API_AUTH_HEADER_NAME] = WAHA_API_KEY
        else:
            header_name = WAHA_API_AUTH_HEADER_NAME or "X-Api-Key"
            headers[header_name] = WAHA_API_KEY
    return headers


async def _try_send(
    client: httpx.AsyncClient,
    url: str,
    payload: dict,
    headers: dict,
) -> tuple[bool, str]:
    """Coba kirim request dan return (success, detail)."""
    try:
        resp = await client.post(url, json=payload, headers=headers)
        body = resp.text[:500]
        if resp.status_code in (200, 201):
            if '"error"' in body.lower() or '"erro"' in body.lower() or '"status":"fail"' in body.lower():
                logger.warning(f"WAHA returned {resp.status_code} but body indicates error: {body}")
                return False, f"WAHA error in body: {body}"
            logger.info(f"WAHA success: {resp.status_code} - {body[:200]}")
            return True, body
        logger.warning(f"WAHA failed: status={resp.status_code}, body={body}")
        return False, f"status={resp.status_code}, body={body}"
    except httpx.TimeoutException:
        logger.error(f"WAHA timeout after {WAHA_TIMEOUT}s for {url}")
        return False, f"Timeout after {WAHA_TIMEOUT}s"
    except Exception as e:
        logger.error(f"WAHA request error: {type(e).__name__}: {e}")
        return False, str(e)


async def _add_query_token(url: str) -> str:
    """Tambahkan token API key sebagai query parameter jika dikonfigurasi."""
    if WAHA_API_KEY and WAHA_API_KEY_IN == "query":
        param = WAHA_API_KEY_PARAM or "token"
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{param}={WAHA_API_KEY}"
    return url


async def send_text(to: str, message: str) -> bool:
    """Kirim pesan teks ke nomor WhatsApp atau group via WAHA.

    Mencoba beberapa endpoint WAHA secara berurutan dengan timeout panjang:
    1. POST /api/sendText (format WAHA >= 2024)
    2. POST /api/sendText dengan token di body
    3. POST /api/sendText dengan token di query string
    """
    chat_id = _ensure_chat_id(to)
    headers = _get_headers()
    logger.info(f"[WAHA] Starting send to {chat_id} (timeout={WAHA_TIMEOUT}s)")

    async with httpx.AsyncClient(timeout=WAHA_TIMEOUT) as client:
        # Attempt 1: /api/sendText dengan session di body
        url = f"{WAHA_API_URL}/sendText"
        payload = {
            "session": WAHA_SESSION_NAME,
            "chatId": chat_id,
            "text": message,
        }
        logger.info(f"[WAHA] Attempt 1: POST {url}")
        ok, detail = await _try_send(client, url, payload, headers)
        if ok:
            return True
        logger.info(f"[WAHA] Attempt 1 failed: {detail}")

        # Attempt 2: /api/sendText dengan token di body
        if WAHA_API_KEY:
            url2 = f"{WAHA_API_URL}/sendText"
            payload2 = {
                "session": WAHA_SESSION_NAME,
                "chatId": chat_id,
                "text": message,
                WAHA_API_KEY_PARAM or "token": WAHA_API_KEY,
            }
            logger.info(f"[WAHA] Attempt 2: POST {url2} (key in body)")
            ok, detail = await _try_send(client, url2, payload2, headers)
            if ok:
                return True
            logger.info(f"[WAHA] Attempt 2 failed: {detail}")

        # Attempt 3: /api/sendText dengan token di query string
        if WAHA_API_KEY and WAHA_API_KEY_IN == "query":
            url3 = await _add_query_token(f"{WAHA_API_URL}/sendText")
            payload3 = {
                "session": WAHA_SESSION_NAME,
                "chatId": chat_id,
                "text": message,
            }
            logger.info(f"[WAHA] Attempt 3: POST {url3} (key in query)")
            ok, detail = await _try_send(client, url3, payload3, headers)
            if ok:
                return True
            logger.info(f"[WAHA] Attempt 3 failed: {detail}")

        logger.error(f"[WAHA] All attempts failed to send to {chat_id}")
        return False


async def _send_group_or_it_fallback(message: str, group_id: Optional[str], it_number: Optional[str]) -> bool:
    """Send notification to group first and fall back to IT number when group send fails."""
    if group_id:
        sent = await send_text(group_id, message)
        if sent:
            return True
        if it_number:
            logger.warning("WAHA_GROUP_ID send failed, falling back to WAHA_IT_NUMBER")
            return await send_text(it_number, message)
        return False
    if it_number:
        return await send_text(it_number, message)
    logger.warning("No WAHA_GROUP_ID or WAHA_IT_NUMBER configured for notification")
    return False


async def notify_tiket_baru(
    nomor_tiket: str,
    nama_pelapor: str,
    ruangan: str,
    kerusakan: str,
    deskripsi: str = "",
) -> bool:
    """Kirim notifikasi tiket baru ke grup IT atau fallback ke IT number."""
    desc_line = f"\nDeskripsi: {deskripsi}" if deskripsi else ""
    message = (
        f"\U0001f514 *Tiket Baru*\n\n"
        f"No Tiket : {nomor_tiket}\n"
        f"Pelapor  : {nama_pelapor}\n"
        f"Ruangan  : {ruangan}\n"
        f"Kerusakan: {kerusakan}"
        f"{desc_line}\n\n"
        f"Silakan ditindaklanjuti."
    )
    return await _send_group_or_it_fallback(message, WAHA_GROUP_ID, WAHA_IT_NUMBER)


async def notify_tiket_created_to_pelapor(
    no_whatsapp: str,
    nomor_tiket: str,
    nama_pelapor: str,
    ruangan: str,
    kerusakan: str,
    deskripsi: str = "",
) -> bool:
    """Kirim template konfirmasi tiket baru ke nomor pelapor."""
    normalized = _normalize_whatsapp_number(no_whatsapp)
    if not normalized:
        logger.warning("WAHA ticket confirmation skipped: no_whatsapp is empty")
        return False
    desc_line = f"\nDeskripsi: {deskripsi}" if deskripsi else ""
    message = (
        f"\u2705 *Tiket Anda Berhasil Dibuat*\n\n"
        f"No Tiket : {nomor_tiket}\n"
        f"Pelapor  : {nama_pelapor}\n"
        f"Ruangan  : {ruangan}\n"
        f"Kerusakan: {kerusakan}"
        f"{desc_line}\n\n"
        f"Status   : Open\n"
        f"Tim IT akan segera menindaklanjuti tiket Anda.\n\n"
        f"Terima kasih."
    )
    return await send_text(normalized, message)


async def notify_tiket_to_it(
    nomor_tiket: str,
    nama_pelapor: str,
    ruangan: str,
    kerusakan: str,
    tiket_id: int | None = None,
    to_number: str | None = None,
) -> bool:
    """Kirim notifikasi tiket baru ke nomor IT (konfigurasi `WAHA_IT_NUMBER`) dengan link."""
    to = to_number or WAHA_IT_NUMBER or WAHA_GROUP_ID
    if not to:
        logger.warning("No target number configured for notify_tiket_to_it")
        return False
    tiket_url = f"{BASE_URL}/tiket/{tiket_id}" if tiket_id else None
    link_text = f"\n\U0001f517 Link: {tiket_url}" if tiket_url else ""
    message = (
        f"\U0001f514 *Tiket Baru (untuk IT)*\n\n"
        f"No Tiket : {nomor_tiket}\n"
        f"Pelapor  : {nama_pelapor}\n"
        f"Ruangan  : {ruangan}\n"
        f"Kerusakan: {kerusakan}\n"
        f"{link_text}\n\n"
        f"Buka tiket di dashboard untuk menindaklanjuti."
    )
    return await send_text(to, message)


async def notify_status_to_it(
    nomor_tiket: str,
    status: str,
    to_number: str | None = None,
    nama_pelapor: Optional[str] = None,
    ruangan: Optional[str] = None,
    kerusakan: Optional[str] = None,
    deskripsi: Optional[str] = None,
    tanggal: Optional[str] = None,
    durasi: Optional[str] = None,
) -> bool:
    """Kirim notifikasi perubahan status ke grup IT atau nomor IT."""
    to = to_number or WAHA_IT_NUMBER
    if WAHA_GROUP_ID:
        message_target = WAHA_GROUP_ID
    elif to:
        message_target = to
    else:
        logger.warning("No target number configured for notify_status_to_it")
        return False
    if status == "Selesai":
        details = []
        if nama_pelapor:
            details.append(f"Pelapor: {nama_pelapor}")
        if ruangan:
            details.append(f"Ruangan: {ruangan}")
        if kerusakan:
            details.append(f"Kerusakan: {kerusakan}")
        if deskripsi:
            details.append(f"Deskripsi: {deskripsi}")
        if tanggal:
            details.append(f"Tanggal: {tanggal}")
        detail_text = "\n".join(details)
        message = (
            f"\u2705 *Tiket Selesai*\n\n"
            f"No Tiket : {nomor_tiket}\n"
            f"Status   : {status}\n"
            f"{detail_text}\n"
            f"Durasi   : {durasi or '-'}\n\n"
            f"Terima kasih."
        )
    else:
        message = f"Tiket {nomor_tiket} status: {status}."

    if WAHA_GROUP_ID:
        return await _send_group_or_it_fallback(message, WAHA_GROUP_ID, to)
    return await send_text(message_target, message)


async def notify_status_change(
    no_whatsapp: str,
    nomor_tiket: str,
    status: str,
    nama_pelapor: Optional[str] = None,
    ruangan: Optional[str] = None,
    kerusakan: Optional[str] = None,
    deskripsi: Optional[str] = None,
    durasi: Optional[str] = None,
) -> bool:
    """Kirim notifikasi perubahan status ke pelapor."""
    normalized_target = _normalize_whatsapp_number(no_whatsapp)
    if not normalized_target:
        logger.warning("WAHA status update skipped: no_whatsapp is empty")
        return False

    messages = {
        "On Progress": f"\U0001f527 Tiket {nomor_tiket} sedang dikerjakan oleh Tim IT.",
        "Selesai": (
            f"\u2705 Tiket {nomor_tiket} telah selesai dikerjakan.\n\n"
            f"Pelapor: {nama_pelapor or '-'}\n"
            f"Ruangan: {ruangan or '-'}\n"
            f"Kerusakan: {kerusakan or '-'}\n"
            f"Deskripsi: {deskripsi or '-'}\n"
            f"Durasi: {durasi or '-'}\n\n"
            f"Silakan lakukan pengecekan. Terima kasih."
        ),
        "Pending": f"\u23f8\ufe0f Tiket {nomor_tiket} untuk sementara ditunda (Pending).",
    }

    message = messages.get(status)
    if not message:
        logger.warning(f"Unknown status for notification: {status}")
        return False

    logger.info(f"Sending status change notification to {normalized_target}: status={status}")
    result = await send_text(normalized_target, message)
    logger.info(f"Status change notification to {normalized_target}: {'SUCCESS' if result else 'FAILED'}")
    return result
