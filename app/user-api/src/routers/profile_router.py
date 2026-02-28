"""User profile API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from src.core import settings
from src.core.config import get_jwt_public_key
from src.dtos import UserProfileDto
from src.models import UserProfile
from src.service import get_profile, upsert_profile


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # token issued by auth-api

router = APIRouter(tags=["profiles"])


def get_current_user_id(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    public_key = get_jwt_public_key()
    if not public_key:
        raise credentials_exception
    try:
        payload = jwt.decode(
            token, public_key, algorithms=[settings.JWT_ALGORITHM]
        )
        sub: str | None = payload.get("sub")
        if sub is None:
            raise credentials_exception
        return sub
    except JWTError:
        raise credentials_exception


@router.get("/profiles/me", response_model=UserProfileDto)
async def get_my_profile(
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> UserProfileDto:
    profile: UserProfile = get_profile(user_id)
    return UserProfileDto(**profile.model_dump())


@router.put("/profiles/me", response_model=UserProfileDto)
async def update_my_profile(
    dto: UserProfileDto,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> UserProfileDto:
    profile = UserProfile(**dto.model_dump())
    saved = upsert_profile(user_id, profile)
    return UserProfileDto(**saved.model_dump())

