import time
from collections import defaultdict
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.security.identity import request_identity

# (method, path under /api/v1) -> (limit, window seconds). Everything else uses RATE_LIMIT_PER_MINUTE.
ENDPOINT_LIMITS: dict[tuple[str, str], tuple[int, int]] = {
    ("POST", "/auth/request-otp"): (5, 60),
    ("POST", "/auth/verify-otp"): (10, 60),
    ("POST", "/auth/register"): (5, 60),
    ("POST", "/auth/refresh"): (10, 60),
    ("POST", "/auth/logout"): (5, 60),
    ("POST", "/auth/logout_all"): (2, 3600),
}


class RateLimiter:
    """Sliding-window limiter. In-memory, so per instance: on serverless it is best-effort
    (OTP request limits are enforced durably in the database). Swap for Redis to make it global."""

    def __init__(self):
        self._records: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int, int]:
        now = time.time()
        history = [ts for ts in self._records[key] if ts > now - window_seconds]
        reset_time = int(now + window_seconds)
        if len(history) >= limit:
            self._records[key] = history
            return False, 0, reset_time
        history.append(now)
        self._records[key] = history
        return True, limit - len(history), reset_time

    def clear(self) -> None:
        self._records.clear()


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.removeprefix("/api/v1")
        endpoint = (request.method, path)
        limit, window = ENDPOINT_LIMITS.get(endpoint, (settings.RATE_LIMIT_PER_MINUTE, 60))
        scope = path if endpoint in ENDPOINT_LIMITS else "global"
        allowed, remaining, reset = rate_limiter.is_allowed(f"{scope}:{request_identity(request)}", limit, window)
        headers = {"X-RateLimit-Limit": str(limit), "X-RateLimit-Remaining": str(remaining), "X-RateLimit-Reset": str(reset)}

        if not allowed:
            return JSONResponse(
                status_code=429,
                headers={**headers, "Retry-After": str(window)},
                content={
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Too many requests. Please slow down.",
                        "field": None,
                        "details": [],
                        "doc_url": "https://docs.akam.app/errors/RATE_LIMITED",
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                },
            )

        response = await call_next(request)
        response.headers.update(headers)
        return response
