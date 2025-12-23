from fastapi import FastAPI

from .routers.chat_router import router as chat_router
from .routers.helper_router import router as helper_router

app = FastAPI()

app.include_router(chat_router)
app.include_router(helper_router)