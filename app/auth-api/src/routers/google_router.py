from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from jose import jwt as jose_jwt

from code_shared.core.exceptions import AppError

from src.core.config import settings
from src.core.dependency import get_auth_service
from src.core.external.google import google_auth
from src.service.auth_service import AuthService

# ---------------------- Set up -------------------->

router = APIRouter(prefix="/auth", tags=["auth", "oidc"])

# ---------------------- Login via Google ------------------------>

@router.get("/login/google")
async def login_google(request: Request):
    redirect_uri = str(request.url_for("auth_callback_google"))
    return await google_auth.google.authorize_redirect(request, redirect_uri)

# --------------------- Callback url ----------------------->

@router.get("/callback/google", name="auth_callback_google")
async def callback_google(
    request: Request,
    service: AuthService = Depends(get_auth_service)
):
    try:
        token = await google_auth.google.authorize_access_token(request)
    except Exception as e:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}?error=oauth&message={e!s}",
            status_code=302,
        )
    try:
        user_info = await google_auth.google.parse_id_token(request, token)
    except Exception:
        user_info = token.get("userinfo") or {}
    if not user_info:
        id_token = token.get("id_token")
        if id_token:
            decoded = jose_jwt.get_unverified_claims(id_token)
            user_info = {
                "sub": decoded.get("sub"),
                "email": decoded.get("email") or "",
                "name": decoded.get("name") or decoded.get("email") or "",
            }
        else:
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}?error=oauth&message=no_userinfo",
                status_code=302,
            )
    sub = user_info.get("sub") or ""
    email = user_info.get("email") or ""
    name = user_info.get("name") or email or sub
    if not sub:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}?error=oauth&message=no_sub",
            status_code=302,
        )
    try:
        _, token, _ = await service.login_or_register_oidc(
            "google", sub, email, name
        )
    except AppError as e:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}?error=oauth&message={e.message!s}",
            status_code=302,
        )
    frontend = settings.FRONTEND_URL.rstrip("/")
    response = RedirectResponse(
        url=f"{frontend}?access_token={token.access_token}",
        status_code=302,
    )
    response.set_cookie(
        key="refresh_token",
        value=token.refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        samesite="lax",
        secure=False,
        path="/",
    )
    return response
