from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
import uuid

from src.core.helper import get_jwt_private_key, settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    private_key = get_jwt_private_key()
    if not private_key:
        raise ValueError("JWT_PRIVATE_KEY or JWT_PRIVATE_KEY_PATH must be set for RS256")
    return jwt.encode(
        to_encode, private_key, algorithm=settings.JWT_ALGORITHM
    )

def create_refresh_token() -> str:
    return str(uuid.uuid4())