"""
Helper API router for health checks and utilities.
"""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
def health_check(request: Request):
    """Check API and database connectivity status."""
    db_alive = False
    try:
        db_alive = request.app.state.db.client.is_live()
    except Exception:
        pass

    return {
        "status": "online",
        "database": "connected" if db_alive else "disconnected",
    }
