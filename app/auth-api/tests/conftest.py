"""Set test RSA key paths before app/config are loaded."""
import os
from pathlib import Path

_fixtures = Path(__file__).resolve().parent / "fixtures"
_private = _fixtures / "rsa_private.pem"
_public = _fixtures / "rsa_public.pem"
if _private.is_file() and _public.is_file():
    os.environ.setdefault("JWT_PRIVATE_KEY_PATH", str(_private))
    os.environ.setdefault("JWT_PUBLIC_KEY_PATH", str(_public))
