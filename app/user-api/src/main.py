from fastapi import FastAPI

from src.core import settings
from src.routers import profile_router


app = FastAPI(title="user-api")
app.include_router(profile_router)

