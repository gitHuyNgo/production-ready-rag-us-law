import os
from src.core.config import settings

def _load_pem(path: str) -> str:
    """Return PEM string from path (if set) or from content. Normalizes \\n from env."""
    if path and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def get_jwt_private_key() -> str:
    return _load_pem(settings.JWT_PRIVATE_KEY_PATH)

def get_jwt_public_key() -> str:
    return _load_pem(settings.JWT_PUBLIC_KEY_PATH)