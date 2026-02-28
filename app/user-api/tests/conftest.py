"""Set test RSA public key path before app/config are loaded."""
import os
from pathlib import Path

_fixtures = Path(__file__).resolve().parent / "fixtures"
_public = _fixtures / "rsa_public.pem"
if _public.is_file():
    os.environ.setdefault("JWT_PUBLIC_KEY_PATH", str(_public))
