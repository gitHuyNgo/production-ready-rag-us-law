from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from src.dtos.auth import RegisterRequest, Token, UserOut

from src.core.dependency import get_auth_service
from src.service.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut)
async def register(
    body: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> UserOut:
    try:
        return await service.register(body.username, body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: AuthService = Depends(get_auth_service),
) -> Token:
    try:
        return service.login(form_data.username, form_data.password)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.get("/me", response_model=UserOut)
async def read_users_me(
    token: Annotated[str, Depends(oauth2_scheme)],
    service: AuthService = Depends(get_auth_service),
) -> UserOut:
    try:
        return service.get_current_user_from_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )