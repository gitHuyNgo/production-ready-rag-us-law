from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from src.core.config import settings
from src.core.dependency import get_auth_service
from src.dtos.auth import RegisterRequest, Token, UserOut
from src.service.auth_service import AuthService

# ---------------------- Set up -------------------->

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------- Register ---------------------->

@router.post("/register", response_model=UserOut)
async def register(
    body: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> UserOut:
    return await service.register(body.username, body.email, body.password)

# ---------------------- Login --------------------->

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> Token:
    data = service.login(form_data.username, form_data.password)
    response.set_cookie(
        key="refresh_token",
        value=data.refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        samesite="lax",
        secure=False,
        path="/",
    )
    return data

# ----------------------- Me --------------------->

@router.get("/me", response_model=UserOut)
async def read_users_me(
    token: Annotated[str, Depends(oauth2_scheme)],
    service: AuthService = Depends(get_auth_service),
) -> UserOut:
    return service.get_current_user_from_token(token)