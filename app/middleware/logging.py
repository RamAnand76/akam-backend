import hashlib
import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()

NEVER_LOG = {
    "content",
    "transcript",
    "label",
    "access_token",
    "refresh_token",
    "fcm_token",
    "audio_file",
    "query",
    "body",
}


def hash_user_id(user_id: str | None) -> str | None:
    if not user_id:
        return None
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16]


class StructlogLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.monotonic()
        request_id = getattr(request.state, "request_id", "unknown")
        user_id = getattr(request.state, "user_id", None)
        client_version = request.headers.get("X-Client-Version", "unknown")
        device_platform = request.headers.get("X-Device-Platform", "unknown")

        response: Response = await call_next(request)
        latency_ms = round((time.monotonic() - start_time) * 1000, 2)

        logger.info(
            "request_processed",
            request_id=request_id,
            user_id_hash=hash_user_id(user_id),
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            latency_ms=latency_ms,
            client_version=client_version,
            device_platform=device_platform,
        )

        return response
