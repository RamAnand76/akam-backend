# Vercel ASGI entry point
# Vercel's @vercel/python runtime imports this file and looks for 'app'.
import json
import os
import sys
import traceback
from datetime import datetime

# Ensure project root is in sys.path so 'app' can always be imported in serverless runtimes
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from app.main import app  # noqa: F401
except Exception as exc:
    err_tb = traceback.format_exc()
    sys.stderr.write(f"[AKAM_BOOT_ERROR] Failed to start application:\n{err_tb}\n")
    sys.stderr.flush()

    async def app(scope, receive, send):
        """Fallback ASGI application when backend initialization fails (e.g. missing env vars)."""
        if scope["type"] == "http":
            body = json.dumps(
                {
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "SERVER_BOOT_ERROR",
                        "message": "Akam backend failed to initialize on Vercel.",
                        "details": [
                            str(exc),
                            "Check Vercel Project Settings -> Environment Variables.",
                            "Required: DATABASE_URL, OTP_HASH_SECRET, RESEND_API_KEY, etc.",
                        ],
                        "traceback": err_tb.splitlines()[-8:],
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            ).encode("utf-8")

            await send(
                {
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("ascii")),
                    ],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": body,
                }
            )
