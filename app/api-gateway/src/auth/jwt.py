"""
JWT verification for API Gateway.
Uses RS256 and auth-api's public key so tokens issued by auth-api are valid here.
"""
from typing import Optional

from jose import JWTError, jwt

from src.core.config import get_jwt_public_key, settings


def verify_token(token: str) -> Optional[str]:
    """
    Verify JWT and return subject (username/user_id) or None if invalid.
    """
    public_key = get_jwt_public_key()
    if not public_key:
        return None
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[settings.JWT_ALGORITHM],
        )
        sub = payload.get("sub")
        return str(sub) if sub is not None else None
    except JWTError:
        return None
