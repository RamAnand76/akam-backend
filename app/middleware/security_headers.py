from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        headers = response.headers
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-Frame-Options"] = "DENY"
        headers["Referrer-Policy"] = "no-referrer"
        # For documentation routes, allow CDN assets needed for Swagger UI
        if request.url.path in ("/docs", "/docs/", "/openapi.json"):
            headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com;"
            )
        else:
            headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
            headers["Cache-Control"] = "no-store, max-age=0"

        headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response
