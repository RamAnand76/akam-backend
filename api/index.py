import sys
import traceback

try:
    from app.main import app  # noqa: F401
except Exception as e:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    
    app = FastAPI()
    
    error_traceback = traceback.format_exc()
    print(f"CRITICAL IMPORT ERROR:\n{error_traceback}", file=sys.stderr)
    
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
    async def fallback_handler(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "FUNCTION_INVOCATION_FAILED (Caught by api/index.py fallback)",
                "type": type(e).__name__,
                "message": str(e),
                "traceback": error_traceback
            }
        )
