from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.config import settings
from app.db.base import Base
from app.db.session import engine
from app.exceptions import AkamException
from app.middleware.idempotency import IdempotencyMiddleware
from app.middleware.logging import StructlogLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.routers import (
    auth,
    briefing,
    chat,
    clusters,
    digest,
    events,
    graph,
    nudges,
    search,
    user,
    websocket,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup (zero friction on SQLite)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


from fastapi.openapi.docs import get_swagger_ui_html


app = FastAPI(
    title="Akam Backend API",
    version="2.0.0",
    docs_url=None,  # Custom dark theme endpoint registered below
    redoc_url=None,
    lifespan=lifespan,
)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    response = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Akam Backend API — Swagger UI (Dark)",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
    )
    dark_css = """
    <style>
        /* ── Globals ─────────────────────────────────────────────── */
        body, .swagger-ui {
            background: #0d1117 !important;
            color: #c9d1d9 !important;
        }

        /* ── Top info bar ────────────────────────────────────────── */
        .swagger-ui .topbar { display: none !important; }
        .swagger-ui .info { margin: 20px 0; }
        .swagger-ui .info .title,
        .swagger-ui .info h1,
        .swagger-ui .info h2,
        .swagger-ui .info p { color: #e6edf3 !important; }
        .swagger-ui .info a { color: #58a6ff !important; }

        /* ── Scheme / server selector ────────────────────────────── */
        .swagger-ui .scheme-container {
            background: #161b22 !important;
            box-shadow: none !important;
            border-bottom: 1px solid #30363d !important;
        }
        .swagger-ui select {
            background: #21262d !important;
            color: #c9d1d9 !important;
            border: 1px solid #30363d !important;
        }
        .swagger-ui label { color: #8b949e !important; }

        /* ── Section headers ─────────────────────────────────────── */
        .swagger-ui .opblock-tag {
            color: #e6edf3 !important;
            border-bottom: 1px solid #30363d !important;
        }
        .swagger-ui .opblock-tag:hover { background: #161b22 !important; }

        /* ── Operation blocks ────────────────────────────────────── */
        .swagger-ui .opblock {
            background: #161b22 !important;
            border: 1px solid #30363d !important;
            box-shadow: none !important;
        }
        .swagger-ui .opblock .opblock-summary {
            border-bottom: 1px solid #30363d !important;
        }
        .swagger-ui .opblock .opblock-summary-description,
        .swagger-ui .opblock .opblock-summary-path {
            color: #c9d1d9 !important;
        }
        .swagger-ui .opblock-body { background: #0d1117 !important; }
        .swagger-ui .opblock-section-header {
            background: #161b22 !important;
            border-bottom: 1px solid #30363d !important;
        }
        .swagger-ui .opblock-section-header h4 { color: #8b949e !important; }

        /* ── Inputs & textareas ──────────────────────────────────── */
        .swagger-ui input,
        .swagger-ui textarea {
            background: #21262d !important;
            color: #c9d1d9 !important;
            border: 1px solid #30363d !important;
            border-radius: 6px !important;
        }
        .swagger-ui input::placeholder,
        .swagger-ui textarea::placeholder { color: #484f58 !important; }

        /* ── Buttons ─────────────────────────────────────────────── */
        .swagger-ui .btn {
            background: #21262d !important;
            color: #c9d1d9 !important;
            border: 1px solid #30363d !important;
        }
        .swagger-ui .btn:hover { background: #30363d !important; }
        .swagger-ui .btn.execute {
            background: #238636 !important;
            color: #fff !important;
            border-color: #238636 !important;
        }
        .swagger-ui .btn.execute:hover { background: #2ea043 !important; }
        .swagger-ui .btn.authorize {
            background: transparent !important;
            color: #10b981 !important;
            border: 2px solid #10b981 !important;
        }
        .swagger-ui .btn.authorize svg { fill: #10b981 !important; }
        .swagger-ui .btn.cancel { border-color: #f85149 !important; color: #f85149 !important; }

        /* ── Tables ──────────────────────────────────────────────── */
        .swagger-ui table thead tr th,
        .swagger-ui .parameters-col_description,
        .swagger-ui .parameters-col_name { color: #8b949e !important; }
        .swagger-ui table.headers td { color: #c9d1d9 !important; }
        .swagger-ui .parameter__name { color: #e6edf3 !important; }
        .swagger-ui .parameter__type { color: #7ee787 !important; }
        .swagger-ui .parameter__in { color: #79c0ff !important; }

        /* ── Code / pre blocks (curl, request body, response) ────── */
        .swagger-ui .highlight-code,
        .swagger-ui pre.microlight,
        .swagger-ui .body-param__text,
        .swagger-ui .curl-command,
        .swagger-ui textarea.curl {
            background: #161b22 !important;
            color: #c9d1d9 !important;
            border: 1px solid #30363d !important;
            border-radius: 6px !important;
        }
        .swagger-ui .microlight span { color: #7ee787 !important; }

        /* ── Response section ────────────────────────────────────── */
        .swagger-ui .responses-wrapper { background: #0d1117 !important; }
        .swagger-ui .response-col_status { color: #c9d1d9 !important; }
        .swagger-ui .response-col_links { color: #8b949e !important; }
        .swagger-ui .response .response-col_description { color: #c9d1d9 !important; }
        .swagger-ui .live-responses-table { border-color: #30363d !important; }

        /* ── URL bar ─────────────────────────────────────────────── */
        .swagger-ui .request-url pre,
        .swagger-ui .url { background: #161b22 !important; color: #58a6ff !important; }

        /* ── Model / schema panel ────────────────────────────────── */
        .swagger-ui .model-box,
        .swagger-ui section.models { background: #161b22 !important; border-color: #30363d !important; }
        .swagger-ui .model-title,
        .swagger-ui .model-title span { color: #e6edf3 !important; }
        .swagger-ui .model { color: #c9d1d9 !important; }
        .swagger-ui .prop-type { color: #7ee787 !important; }
        .swagger-ui .prop-format { color: #79c0ff !important; }

        /* ── Auth modal ──────────────────────────────────────────── */
        .swagger-ui .dialog-ux .modal-ux {
            background: #161b22 !important;
            border: 1px solid #30363d !important;
        }
        .swagger-ui .dialog-ux .modal-ux-header { border-bottom: 1px solid #30363d !important; }
        .swagger-ui .dialog-ux .modal-ux-header h3 { color: #e6edf3 !important; }
        .swagger-ui .dialog-ux .modal-ux-content p,
        .swagger-ui .dialog-ux .modal-ux-content h4 { color: #c9d1d9 !important; }
        .swagger-ui .wrapper { background: transparent !important; }

        /* ── Miscellaneous ───────────────────────────────────────── */
        .swagger-ui .arrow { fill: #8b949e !important; }
        .swagger-ui svg { fill: currentColor; }
        .swagger-ui .loading-container .loading { color: #c9d1d9 !important; }
        .swagger-ui hr { border-color: #30363d !important; }
        .swagger-ui h1, .swagger-ui h2, .swagger-ui h3,
        .swagger-ui h4, .swagger-ui h5 { color: #e6edf3 !important; }
        .swagger-ui p,
        .swagger-ui span,
        .swagger-ui div { color: inherit; }
    </style>
    """
    html = response.body.decode("utf-8")
    html = html.replace("</head>", f"{dark_css}</head>")
    return HTMLResponse(content=html)

# 1. Security & Context Middleware Stack (executed bottom-to-top)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(StructlogLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)


# 2. Standard FAANG Envelope Error Handlers
def _error_envelope(request: Request, status_code: int, code: str, message: str, details: list = None, field: str = None):
    req_id = getattr(request.state, "request_id", "01J4MXYZ")
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "error": {
                "code": code,
                "message": message,
                "field": field,
                "details": details or [],
                "doc_url": f"https://docs.akam.app/errors/{code}",
            },
            "meta": {
                "request_id": req_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": "2.0.0",
            },
        },
    )


@app.exception_handler(AkamException)
async def akam_exception_handler(request: Request, exc: AkamException):
    return _error_envelope(
        request=request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        field=exc.field,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = []
    for err in exc.errors():
        field_loc = " -> ".join([str(x) for x in err.get("loc", []) if x not in ("body",)])
        details.append({
            "field": field_loc or None,
            "message": err.get("msg", "Validation error"),
            "value_received": None,
        })
    return _error_envelope(
        request=request,
        status_code=422,
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        details=details,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code = "INTERNAL_ERROR" if exc.status_code == 500 else "HTTP_ERROR"
    if exc.status_code == 404:
        code = "ENTITY_NOT_FOUND"
    elif exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"

    return _error_envelope(
        request=request,
        status_code=exc.status_code,
        code=code,
        message=str(exc.detail),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return _error_envelope(
        request=request,
        status_code=500,
        code="INTERNAL_ERROR",
        message="An unexpected error occurred.",
    )


# 3. Include Routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(graph.router)
app.include_router(clusters.router)
app.include_router(events.router)
app.include_router(nudges.router)
app.include_router(briefing.router)
app.include_router(search.router)
app.include_router(digest.router)
app.include_router(user.router)
app.include_router(websocket.router)
