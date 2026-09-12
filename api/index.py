# Vercel ASGI entry point
# Vercel's @vercel/python runtime imports this file and looks for 'app'.
# All application logic lives in app/main.py; this is just a re-export.
from app.main import app  # noqa: F401
