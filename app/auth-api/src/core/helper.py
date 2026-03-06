from src.core.config import settings


def get_jwt_private_key() -> str:
    return settings.JWT_PRIVATE_KEY


def get_jwt_public_key() -> str:
    return settings.JWT_PUBLIC_KEY