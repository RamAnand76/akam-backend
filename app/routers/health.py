from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db.session import async_session_factory
from app.models.schemas.common import ApiResponse, Meta

router = APIRouter(tags=["health"])


def _meta(request: Request) -> Meta:
    return Meta(request_id=getattr(request.state, "request_id", "unknown"), timestamp=datetime.utcnow(), version="2.0.0")


@router.get("/health", response_model=ApiResponse[dict])
async def health(request: Request) -> ApiResponse[dict]:
    """Liveness: the process is up."""
    return ApiResponse(data={"status": "ok"}, meta=_meta(request))


@router.get("/ready")
async def ready(request: Request):
    """Readiness: the database answers."""
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "data": None,
                "error": {"code": "NOT_READY", "message": "Database unavailable.", "field": None, "details": [], "doc_url": "https://docs.akam.app/errors/NOT_READY"},
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        )
    return ApiResponse(data={"status": "ready"}, meta=_meta(request))
