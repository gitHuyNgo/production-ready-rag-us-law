"""
Google OIDC: GET /auth/login/google (redirect to Google), GET /auth/callback/google (exchange code, issue token, redirect to frontend).
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from jose import jwt as jose_jwt

from src.core.config import settings
from src.core.external.google import google_auth
from src.core.dependency import get_auth_service
from src.service.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth", "oidc"])


@router.get("/login/google")
async def login_google(request: Request):
    redirect_uri = str(request.url_for("auth_callback_google"))
    return await google_auth.google.authorize_redirect(request, redirect_uri)


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
        _, access_token_obj, _ = await service.login_or_register_oidc(
            "google", sub, email, name
        )
    except Exception as e:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}?error=oauth&message={e!s}",
            status_code=302,
        )
    frontend = settings.FRONTEND_URL.rstrip("/")
    return RedirectResponse(
        url=f"{frontend}?token={access_token_obj.access_token}",
        status_code=302,
    )
