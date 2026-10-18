import os
import time
import uuid
from functools import lru_cache

import structlog
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError, JWKError

from app.config import settings
from app.exceptions import UnauthorizedException

ALGORITHM = "RS256"
logger = structlog.get_logger()


def _pem(value: str, is_public: bool = True) -> bytes:
    """Normalize and format PEM keys from env vars, literal strings, files, or raw base64."""
    if not value or not value.strip():
        return b""
    v = value.strip().strip('"\'')
    # Support literal and escaped newlines / returns
    v = v.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")
    v = v.replace("\r\n", "\n").replace("\r", "\n")
    v = v.strip().strip('"\'').strip()

    # If the user passed a file path by mistake
    if os.path.exists(v):
        try:
            with open(v, "r", encoding="utf-8") as f:
                v = f.read().strip()
        except Exception:
            pass

    # If missing PEM headers/footers (e.g. user pasted raw base64)
    if "-----BEGIN" not in v:
        header = "-----BEGIN PUBLIC KEY-----" if is_public else "-----BEGIN PRIVATE KEY-----"
        footer = "-----END PUBLIC KEY-----" if is_public else "-----END PRIVATE KEY-----"
        clean_b64 = "".join(v.split())
        lines = [clean_b64[i : i + 64] for i in range(0, len(clean_b64), 64)]
        v = f"{header}\n" + "\n".join(lines) + f"\n{footer}"

    return v.encode("utf-8")


@lru_cache(maxsize=1)
def _keys() -> tuple[bytes, bytes]:
    """PEM keypair from env. Only in development an ephemeral keypair is generated (tokens die on restart)."""
    if settings.JWT_PRIVATE_KEY:
        priv = _pem(settings.JWT_PRIVATE_KEY, is_public=False)
        pub = _pem(settings.JWT_PUBLIC_KEY, is_public=True)
        try:
            serialization.load_pem_private_key(priv, password=None)
            serialization.load_pem_public_key(pub)
            return priv, pub
        except Exception as e:
            logger.error("jwt_keys_load_failed", error=str(e))
            if not settings.is_deployed:
                logger.warning("jwt_keys_fallback_ephemeral", detail="Falling back to in-memory keys in dev")
            else:
                raise ValueError(f"Unable to load PEM keys from environment: {e}") from e

    logger.warning("jwt_ephemeral_keys", detail="JWT_PRIVATE_KEY unset; generated an in-memory keypair (development only)")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    pub = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return priv, pub


def _encode(user_id: str, device_id: str, sid: str, scope: str, ttl: int, jti: str | None = None) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "jti": jti or str(uuid.uuid4()),
        "iat": now,
        "exp": now + ttl,
        "device_id": device_id,
        "sid": sid,
        "scope": scope,
    }
    return jwt.encode(payload, _keys()[0], algorithm=ALGORITHM)


def create_access_token(user_id: str, device_id: str, sid: str) -> str:
    return _encode(user_id, device_id, sid, "user", settings.ACCESS_TOKEN_TTL_SECONDS)


def create_refresh_token(user_id: str, device_id: str, sid: str, jti: str) -> str:
    return _encode(user_id, device_id, sid, "refresh", settings.REFRESH_TOKEN_TTL_SECONDS, jti)


def verify_token(token: str) -> dict:
    """Signature + expiry only. Revocation is checked against the database by callers."""
    try:
        return jwt.decode(token, _keys()[1], algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise UnauthorizedException(code="TOKEN_EXPIRED", message="Token has expired.")
    except (JWTError, JWKError, ValueError):
        raise UnauthorizedException(code="TOKEN_INVALID", message="Token is invalid or malformed.")

