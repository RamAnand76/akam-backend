from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings

import os
from pathlib import Path

# Resolve database URL safely for serverless environments (e.g. Vercel read-only filesystem)
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite") and "///" in db_url:
    db_path = db_url.split("///")[-1]
    # If using relative path like ./akam.db or akam.db, use /tmp/akam.db on serverless
    if not os.path.isabs(db_path) or db_path.startswith("./"):
        if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            db_url = "sqlite+aiosqlite:////tmp/akam.db"

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
