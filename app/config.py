import os
from dotenv import load_dotenv

load_dotenv()


def _env_str(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    if value is None:
        return ""
    normalized = value.strip()
    if normalized.lower() in {"", "null", "none"}:
        return ""
    return normalized


# Database
DATABASE_URL = _env_str("DATABASE_URL") or "sqlite:///./helpdesk.db"

# Upload
UPLOAD_DIR = _env_str("UPLOAD_DIR") or "./uploads"

# WAHA Configuration
WAHA_API_URL = _env_str("WAHA_API_URL") or "http://localhost:3000/api"
WAHA_SESSION_NAME = _env_str("WAHA_SESSION_NAME") or "default"
WAHA_GROUP_ID = _env_str("WAHA_GROUP_ID")
WAHA_API_KEY = _env_str("WAHA_API_KEY")

# Optional: customize how the API key is sent to WAHA
# Set `WAHA_API_AUTH_HEADER_NAME` to a header name (e.g. x-waha-key) to send the key in that header.
# Set `WAHA_API_KEY_IN` to one of: "header", "body", "query" to control where to include the key.
WAHA_API_AUTH_HEADER_NAME = _env_str("WAHA_API_AUTH_HEADER_NAME")
WAHA_API_KEY_IN = _env_str("WAHA_API_KEY_IN")
WAHA_API_KEY_PARAM = _env_str("WAHA_API_KEY_PARAM") or "token"

# IT contact for direct notifications (international format, e.g. 62822...)
WAHA_IT_NUMBER = _env_str("WAHA_IT_NUMBER")

# App
BASE_URL = _env_str("BASE_URL") or "http://localhost:8000"
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")

