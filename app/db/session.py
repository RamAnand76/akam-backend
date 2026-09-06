from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings

import os
from pathlib import Path

# On Linux/serverless (Vercel, Lambda, Railway) the project root is read-only.
# Always redirect SQLite to /tmp which is the only writable directory.
# On Windows (local dev) use the configured DATABASE_URL as-is.
if os.name == "nt":
    # Local Windows development — use the configured URL unchanged
    db_url = settings.DATABASE_URL
else:
    # Linux / serverless — force SQLite to /tmp regardless of DATABASE_URL
    if settings.DATABASE_URL.startswith("sqlite"):
        # Ensure the directory exists before SQLAlchemy tries to open the file
        db_dir = Path("/tmp")
        db_dir.mkdir(parents=True, exist_ok=True)
        db_url = "sqlite+aiosqlite:////tmp/akam.db"
    else:
        # Non-SQLite (e.g., Postgres) — pass through as-is
        db_url = settings.DATABASE_URL

# Engine configuration (works for SQLite aiosqlite and PostgreSQL asyncpg)
engine = create_async_engine(
    db_url,
    echo=(settings.APP_ENV == "development"),
    future=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
