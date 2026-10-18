import time
import uuid
from functools import lru_cache

import structlog
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from app.config import settings
from app.exceptions import UnauthorizedException

ALGORITHM = "RS256"
logger = structlog.get_logger()


def _pem(value: str) -> bytes:
    # Support literal and escaped newlines (e.g. from single-line environment variable strings)
    normalized = (
        value.replace(r"\n", "\n")
        .replace("\\n", "\n")
        .strip()
        .strip('"\'')
    )
    return normalized.encode()


@lru_cache(maxsize=1)
def _keys() -> tuple[bytes, bytes]:
    """PEM keypair from env. Only in development an ephemeral keypair is generated (tokens die on restart)."""
    if settings.JWT_PRIVATE_KEY:
        return _pem(settings.JWT_PRIVATE_KEY), _pem(settings.JWT_PUBLIC_KEY)
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
    except JWTError:
        raise UnauthorizedException(code="TOKEN_INVALID", message="Token is invalid or malformed.")
