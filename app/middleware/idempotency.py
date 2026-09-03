import json
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Cache stores key -> (status_code, headers, body, timestamp)
_IDEMPOTENCY_STORE: dict[str, tuple[int, dict[str, str], bytes, float]] = {}
TTL_SECONDS = 86400  # 24 hours


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Idempotency applies to POST requests with Idempotency-Key
        if request.method != "POST":
            return await call_next(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)

        user_id = getattr(request.state, "user_id", "anon")
        cache_key = f"idempotency:{user_id}:{idempotency_key}"

        now = time.time()
        cached = _IDEMPOTENCY_STORE.get(cache_key)
        if cached:
            status_code, headers, body, stored_at = cached
            if now - stored_at < TTL_SECONDS:
                resp_headers = dict(headers)
                resp_headers["Idempotent-Replayed"] = "true"
                return Response(
                    content=body,
                    status_code=status_code,
                    headers=resp_headers,
                    media_type="application/json",
                )

        # Call endpoint handler
        response: Response = await call_next(request)

        # Only cache 200 or 201 responses
        if response.status_code in (200, 201):
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            resp_headers = dict(response.headers)
            _IDEMPOTENCY_STORE[cache_key] = (
                response.status_code,
                resp_headers,
                response_body,
                now,
            )

            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=resp_headers,
                media_type=response.media_type,
            )

        return response
