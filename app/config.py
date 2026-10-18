import json
import re
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: str = "INFO"

    # Database: Postgres (Supabase) in every real environment. SQLite is only used by pytest.
    DATABASE_URL: str = ""

    # Auth / JWT. PEM *contents* (use literal "\n" for newlines if your host needs single-line values).
    # In development only, an ephemeral keypair is generated when both are unset.
    JWT_PRIVATE_KEY: str = ""
    JWT_PUBLIC_KEY: str = ""
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_TTL_SECONDS: int = 3600        # 1 hour
    REFRESH_TOKEN_TTL_SECONDS: int = 2592000    # 30 days

    # Email OTP
    OTP_HASH_SECRET: str = ""                   # HMAC pepper for OTP + device-secret hashing
    OTP_TTL_SECONDS: int = 600
    OTP_MAX_ATTEMPTS: int = 5
    OTP_REQUESTS_PER_EMAIL: int = 3             # per OTP_REQUEST_WINDOW_SECONDS
    OTP_REQUESTS_PER_IP: int = 10               # per OTP_REQUEST_WINDOW_SECONDS
    OTP_REQUEST_WINDOW_SECONDS: int = 3600
    EMAIL_BACKEND: Literal["console", "smtp", "resend"] = "console"
    EMAIL_FROM: str = "Akam <no-reply@akam.app>"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    RESEND_API_KEY: str = ""

    # Legacy device-only registration (insecure: account takeover by device_id). Keep OFF.
    ENABLE_LEGACY_REGISTER: bool = False

    # Rate limiting (requests per minute per user id, else per IP)
    RATE_LIMIT_PER_MINUTE: int = 200

    # On-device model manifest + app config
    MODEL_VERSION: str = ""
    MODEL_URL: str = ""
    MODEL_SHA256: str = ""
    MODEL_SIZE_BYTES: int = 0
    MIN_APP_VERSION: str = "1.0.0"
    FEATURE_FLAGS: str = "{}"                   # JSON object, e.g. {"analytics": true}

    # Gemma & AI (deprecated server-side content endpoints)
    GEMMA_MODEL_NAME: str = "gemma-4"
    GEMINI_API_KEY: str = ""
    GEMMA_API_BASE: str = ""
    AI_FALLBACK_MODE: bool = True

    # Client & app
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8080"  # comma-separated allow-list
    CDN_BASE_URL: str = "https://cdn.akam.app"
    MAX_UPLOAD_SIZE_MB: int = 10

    REDIS_CACHE_TTL_GRAPH: int = 60
    REDIS_CACHE_TTL_BRIEFING: int = 21600
    REDIS_CACHE_TTL_CLUSTERS: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def is_deployed(self) -> bool:
        return self.APP_ENV in ("staging", "production")

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def feature_flags(self) -> dict:
        return json.loads(self.FEATURE_FLAGS or "{}")

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+asyncpg://" + url[len(prefix):]
        return url

    @model_validator(mode="after")
    def _validate(self) -> "Settings":
        if "*" in self.cors_origins:
            raise ValueError("ALLOWED_ORIGINS must be an explicit allow-list; '*' is not permitted (credentials are enabled)")
        try:
            if not isinstance(self.feature_flags, dict):
                raise ValueError
        except ValueError:
            raise ValueError("FEATURE_FLAGS must be a JSON object") from None
        model = (self.MODEL_VERSION, self.MODEL_URL, self.MODEL_SHA256)
        if any(model) and not all(model):
            raise ValueError("MODEL_VERSION, MODEL_URL and MODEL_SHA256 must be set together")
        if self.MODEL_SHA256 and not re.fullmatch(r"[0-9a-fA-F]{64}", self.MODEL_SHA256):
            raise ValueError("MODEL_SHA256 must be 64 hex characters")
        if bool(self.JWT_PRIVATE_KEY) != bool(self.JWT_PUBLIC_KEY):
            raise ValueError("Set both JWT_PRIVATE_KEY and JWT_PUBLIC_KEY, or neither (development only)")
        if self.is_deployed:
            missing = [
                name
                for name in ("DATABASE_URL", "JWT_PRIVATE_KEY", "JWT_PUBLIC_KEY", "OTP_HASH_SECRET")
                if not getattr(self, name)
            ]
            if missing:
                raise ValueError(f"Missing required settings for {self.APP_ENV}: {', '.join(missing)}")
            if not self.async_database_url.startswith("postgresql+asyncpg://"):
                raise ValueError("DATABASE_URL must be a Postgres URL in staging/production")
            if not self.cors_origins:
                raise ValueError("ALLOWED_ORIGINS must list at least one origin in staging/production")
            if self.EMAIL_BACKEND == "console":
                raise ValueError("EMAIL_BACKEND=console would log OTPs; use smtp or resend in staging/production")
            if self.EMAIL_BACKEND == "smtp" and not (self.SMTP_HOST and self.SMTP_USER and self.SMTP_PASSWORD):
                raise ValueError("EMAIL_BACKEND=smtp requires SMTP_HOST, SMTP_USER, SMTP_PASSWORD")
            if self.EMAIL_BACKEND == "resend" and not self.RESEND_API_KEY:
                raise ValueError("EMAIL_BACKEND=resend requires RESEND_API_KEY")
        elif not self.DATABASE_URL:
            raise ValueError("DATABASE_URL is required (Postgres URL; sqlite is for pytest only)")
        return self


settings = Settings()
