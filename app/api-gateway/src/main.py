"""
API Gateway: single entry point for clients.
- Rate limiting (per IP)
- CORS
- JWT verification for protected routes
- HTTP proxy to auth-api, user-api, chat-api
- WebSocket proxy to chat-api
"""
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import FastAPI, Request, WebSocket, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.cors import CORSMiddleware

from src.auth.jwt import verify_token
from src.core.config import settings
from src.proxy.http_proxy import proxy_http
from src.proxy.ws_proxy import proxy_websocket

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# Paths that do not require JWT
# ---------------------------------------------------------------------------
PUBLIC_PREFIXES = ("/auth/register", "/auth/token", "/health", "/docs", "/openapi.json", "/redoc")


def _is_public(path: str) -> bool:
    return path == "/" or any(path.startswith(p) for p in PUBLIC_PREFIXES)


def _get_bearer(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    return auth[7:].strip()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=60.0) as client:
        app.state.http_client = client
        yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="API Gateway",
    description="Single entry point: rate limiting, CORS, JWT verification, proxy to auth/user/chat services.",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Health (gateway liveness)
# ---------------------------------------------------------------------------
@app.get("/health", tags=["health"])
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def health(request: Request):
    return {"status": "ok", "service": "api-gateway"}


@app.get("/", tags=["root"])
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def root(request: Request):
    return {"service": "api-gateway", "docs": "/docs"}


# ---------------------------------------------------------------------------
# Auth API proxy
# ---------------------------------------------------------------------------
@app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def proxy_auth(request: Request, path: str):
    full_path = f"/auth/{path}" if path else "/auth"
    if not _is_public(full_path):
        token = _get_bearer(request)
        sub = verify_token(token) if token else None
        if not sub:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Could not validate credentials"},
                headers={"WWW-Authenticate": "Bearer"},
            )
    else:
        sub = None
    client = request.app.state.http_client
    return await proxy_http(client, settings.AUTH_API_URL, request, full_path, sub=sub)


# ---------------------------------------------------------------------------
# User API proxy (protected)
# ---------------------------------------------------------------------------
@app.api_route("/profiles/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def proxy_profiles(request: Request, path: str):
    token = _get_bearer(request)
    sub = verify_token(token) if token else None
    if not sub:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Could not validate credentials"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    full_path = f"/profiles/{path}" if path else "/profiles"
    client = request.app.state.http_client
    return await proxy_http(client, settings.USER_API_URL, request, full_path, sub=sub)


# ---------------------------------------------------------------------------
# Chat API proxy (HTTP)
# ---------------------------------------------------------------------------
@app.api_route("/chat/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def proxy_chat_http(request: Request, path: str):
    token = _get_bearer(request)
    sub = verify_token(token) if token else None
    if not sub:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Could not validate credentials"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    full_path = f"/chat/{path}" if path else "/chat"
    client = request.app.state.http_client
    return await proxy_http(client, settings.CHAT_API_URL, request, full_path, sub=sub)


# ---------------------------------------------------------------------------
# Chat API WebSocket proxy
# ---------------------------------------------------------------------------
@app.websocket("/chat/")
async def proxy_chat_websocket(websocket: WebSocket):
    token = websocket.headers.get("authorization") or ""
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    sub = verify_token(token) if token else None
    if not sub:
        await websocket.close(code=1008, reason="Unauthorized")
        return
    base = settings.CHAT_API_URL.replace("http://", "ws://").replace("https://", "wss://")
    upstream_path = f"{base.rstrip('/')}/chat/"
    query_string = websocket.scope.get("query_string")
    if query_string:
        qs = query_string.decode("utf-8") if isinstance(query_string, bytes) else query_string
        upstream_path = f"{upstream_path}?{qs}"
    await proxy_websocket(websocket, upstream_path, sub=sub)
