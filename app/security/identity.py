import hashlib
import hmac

from starlette.requests import Request

from app.config import settings
from app.exceptions import AkamException
from app.security.jwt import verify_token


def client_ip(request: Request) -> str:
    # Vercel overwrites X-Forwarded-For with the real client address; revisit on other hosts.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def request_identity(request: Request) -> str:
    """`u:<user id>` from a validly signed bearer token, else `ip:<client ip>`. Runs before routing."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            sub = verify_token(auth[7:].strip()).get("sub")
            if sub:
                return f"u:{sub}"
        except AkamException:
            pass
    return f"ip:{client_ip(request)}"


def keyed_hash(value: str) -> str:
    """HMAC-SHA256 with the server pepper; used for OTP codes, device secrets and IPs at rest."""
    pepper = (settings.OTP_HASH_SECRET or "dev-only-pepper").encode()
    return hmac.new(pepper, value.encode(), hashlib.sha256).hexdigest()
