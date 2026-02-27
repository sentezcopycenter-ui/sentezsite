import os
import re

def env_float(key: str, default: float) -> float:
    v = os.getenv(key)
    if v is None or v == "":
        return float(default)
    return float(str(v).replace(",", "."))

def env_int(key: str, default: int) -> int:
    v = os.getenv(key)
    if v is None or v == "":
        return int(default)
    return int(v)

def env_str(key: str, default: str="") -> str:
    v = os.getenv(key)
    return v if v is not None else default

# Project paths (Windows-safe)
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INSTANCE_DIR = os.path.join(PROJECT_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

def normalize_db_url(url: str) -> str:
    """Normalize sqlite URL to an absolute, writable file under ./instance."""
    url = (url or "").strip()
    if not url:
        db_path = os.path.join(INSTANCE_DIR, "app.db")
        return "sqlite:///" + db_path.replace("\\", "/")

    if url.startswith("sqlite:///"):
        path = url[len("sqlite:///"):]
        if path.startswith("./"):
            path = path[2:]

        # absolute path? (C:\ or /)
        is_abs = bool(re.match(r"^[A-Za-z]:[\\/]", path)) or path.startswith("/")
        if not is_abs:
            path = os.path.join(PROJECT_DIR, path)

        os.makedirs(os.path.dirname(path), exist_ok=True)
        return "sqlite:///" + path.replace("\\", "/")

    return url

class Config:
    SECRET_KEY = env_str("SECRET_KEY", "dev-secret")
    ADMIN_PASSWORD = env_str("ADMIN_PASSWORD", "admin")
    SQLALCHEMY_DATABASE_URI = normalize_db_url(env_str("DATABASE_URL", "sqlite:///./instance/app.db"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # pricing
    PRICE_BW = env_float("PRICE_BW", 0.50)          # TRY per page
    PRICE_COLOR = env_float("PRICE_COLOR", 0.90)    # TRY per page
    PAGES_PER_SHEET = env_int("PAGES_PER_SHEET", 2)

    # shipping
    SHIPPING_ENABLED = env_int("SHIPPING_ENABLED", 1) == 1
    FREE_SHIPPING_LIMIT = env_float("FREE_SHIPPING_LIMIT", 500)
    SHIPPING_FEE = env_float("SHIPPING_FEE", 80)

    # whatsapp / bank
    # Default shop WhatsApp line
    WHATSAPP_NUMBER = env_str("WHATSAPP_NUMBER", "905065086639")
    BANK_RECIPIENT_NAME = env_str("BANK_RECIPIENT_NAME", "")
    BANK_IBAN = env_str("BANK_IBAN", "")

    # uploads
    MAX_CONTENT_LENGTH = env_int("MAX_CONTENT_LENGTH_MB", 30) * 1024 * 1024
