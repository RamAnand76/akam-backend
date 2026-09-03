from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "sqlite+aiosqlite:///./akam.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security & JWT
    JWT_SECRET_KEY: str = "super-secret-default-key-for-local-development-only-change-me"
    JWT_ALGORITHM: str = "RS256"
    JWT_PRIVATE_KEY_PATH: str | None = None
    JWT_PUBLIC_KEY_PATH: str | None = None
    ACCESS_TOKEN_TTL_SECONDS: int = 3600       # 1 hour
    REFRESH_TOKEN_TTL_SECONDS: int = 2592000    # 30 days
    
    # Gemma & AI Model
    GEMMA_MODEL_NAME: str = "gemma-4"
    GEMINI_API_KEY: str = ""
    GEMMA_API_BASE: str = ""  # e.g., http://localhost:11434/v1 for Ollama if used
    AI_FALLBACK_MODE: bool = True  # Allows smooth offline responses during dev/testing
    
    # Client & App configuration
    ALLOWED_ORIGINS: str = "*"
    CDN_BASE_URL: str = "https://cdn.akam.app"
    MAX_UPLOAD_SIZE_MB: int = 10
    
    # Cache TTLs
    REDIS_CACHE_TTL_GRAPH: int = 60
    REDIS_CACHE_TTL_BRIEFING: int = 21600
    REDIS_CACHE_TTL_CLUSTERS: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
