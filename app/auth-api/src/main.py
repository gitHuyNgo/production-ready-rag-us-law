from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from code_shared.core.exceptions import AppError

from src.core.config import settings
from src.events import get_publisher
from src.routers.auth_router import router as auth_router
from src.routers.google_router import router as google_router


def _app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    headers = {}
    if exc.status_code == 401:
        headers["WWW-Authenticate"] = "Bearer"
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
        headers=headers,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.core.external.google import init_google
    import src.events as events_module
    from src.db import init_db
    init_google()
    events_module.publisher = get_publisher()
    if init_db():
        app.state.db_available = True
    else:
        app.state.db_available = False
    yield
    if hasattr(events_module.publisher, "close"):
        await events_module.publisher.close()  # type: ignore


app = FastAPI(title="auth-api", lifespan=lifespan)
app.add_exception_handler(AppError, _app_error_handler)
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)
app.include_router(auth_router)
app.include_router(google_router)
