import os
import time
import uuid
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import JWTError, jwt
from app.config import settings
from app.exceptions import UnauthorizedException

ALGORITHM = "RS256"
ACCESS_TTL = settings.ACCESS_TOKEN_TTL_SECONDS
REFRESH_TTL = settings.REFRESH_TOKEN_TTL_SECONDS

# Directory to hold auto-generated RSA keypair if not mounted from secret
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    KEY_DIR = Path("/tmp/secrets")
else:
    KEY_DIR = Path("./secrets")

PRIVATE_KEY_FILE = KEY_DIR / "jwt_private.pem"
PUBLIC_KEY_FILE = KEY_DIR / "jwt_public.pem"


def _ensure_rsa_keys():
    if settings.JWT_PRIVATE_KEY_PATH and settings.JWT_PUBLIC_KEY_PATH:
        with open(settings.JWT_PRIVATE_KEY_PATH, "rb") as f:
            priv = f.read()
        with open(settings.JWT_PUBLIC_KEY_PATH, "rb") as f:
            pub = f.read()
        return priv, pub

    if not PRIVATE_KEY_FILE.exists() or not PUBLIC_KEY_FILE.exists():
        KEY_DIR.mkdir(parents=True, exist_ok=True)
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        priv = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        PRIVATE_KEY_FILE.write_bytes(priv)
        PUBLIC_KEY_FILE.write_bytes(pub)
    else:
        priv = PRIVATE_KEY_FILE.read_bytes()
        pub = PUBLIC_KEY_FILE.read_bytes()

    return priv, pub


_PRIVATE_KEY, _PUBLIC_KEY = _ensure_rsa_keys()

# In-memory blacklist for JTI (revocation) and token generation store (for logout_all)
_REVOKED_JTIS: dict[str, float] = {}
_USER_TOKEN_GEN: dict[str, int] = {}


def revoke_token(jti: str, ttl: int = REFRESH_TTL):
    _REVOKED_JTIS[jti] = time.time() + ttl


def is_token_revoked(jti: str) -> bool:
    expiry = _REVOKED_JTIS.get(jti)
    if not expiry:
        return False
    if time.time() > expiry:
        _REVOKED_JTIS.pop(jti, None)
        return False
    return True


def invalidate_all_user_sessions(user_id: str, new_gen: int):
    _USER_TOKEN_GEN[user_id] = new_gen


def create_access_token(user_id: str, device_id: str, gen: int = 0) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + ACCESS_TTL,
        "device_id": device_id,
        "scope": "user",
        "gen": gen,
    }
    return jwt.encode(payload, _PRIVATE_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str, device_id: str, gen: int = 0) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + REFRESH_TTL,
        "device_id": device_id,
        "scope": "refresh",
        "gen": gen,
    }
    return jwt.encode(payload, _PRIVATE_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _PUBLIC_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise UnauthorizedException(code="TOKEN_EXPIRED", message="Token is invalid or expired.")

    jti = payload.get("jti")
    if jti and is_token_revoked(jti):
        raise UnauthorizedException(code="TOKEN_REVOKED", message="Token has been revoked.")

    user_id = payload.get("sub")
    current_gen = _USER_TOKEN_GEN.get(user_id, 0)
    token_gen = payload.get("gen", 0)
    if current_gen > token_gen:
        raise UnauthorizedException(code="TOKEN_REVOKED", message="All sessions revoked for this account.")

    return payload
