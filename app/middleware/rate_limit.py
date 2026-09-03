import time
from collections import defaultdict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.exceptions import RateLimitedException


class RateLimiter:
    """Sliding-window in-memory rate limiter, easily swappable with Redis."""
    def __init__(self):
        self._records: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int, int]:
        now = time.time()
        cutoff = now - window_seconds
        
        # Clean older records
        history = [ts for ts in self._records[key] if ts > cutoff]
        remaining = max(0, limit - len(history))
        reset_time = int(now + window_seconds)

        if len(history) >= limit:
            self._records[key] = history
            return False, remaining, reset_time

        history.append(now)
        self._records[key] = history
        return True, remaining - 1, reset_time


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Determine client identifier: authenticated user or client IP
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user_id", None) or client_ip
        
        # Default policy: 200 requests per minute
        allowed, remaining, reset = rate_limiter.is_allowed(f"global:{user_id}", limit=200, window_seconds=60)
        
        if not allowed:
            request_id = getattr(request.state, "request_id", "unknown")
            return JSONResponse(
                status_code=429,
                headers={
                    "X-RateLimit-Limit": "200",
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset),
                    "Retry-After": "60",
                },
                content={
                    "status": "error",
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Too many requests. Please slow down.",
                        "field": None,
                        "details": [],
                        "doc_url": "https://docs.akam.app/errors/RATE_LIMITED",
                    },
                    "meta": {
                        "request_id": request_id,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "version": "2.0.0",
                    },
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = "200"
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset)
        return response
