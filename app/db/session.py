import os
import sqlite3
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

if os.name == "nt":
    # ── Local Windows development ───────────────────────────────────────────
    # Use DATABASE_URL from settings as-is (relative path resolved by SQLite)
    db_url = settings.DATABASE_URL
    engine = create_async_engine(
        db_url,
        echo=(settings.APP_ENV == "development"),
        future=True,
    )
else:
    # ── Linux / Serverless (Vercel, Lambda, Railway) ────────────────────────
    # /var/task is read-only; /tmp is the only writable directory.
    DB_PATH = "/tmp/akam.db"
    db_url = f"sqlite+aiosqlite:///{DB_PATH}"

    # Pre-create the SQLite file synchronously using stdlib sqlite3.
    # This guarantees the file exists BEFORE aiosqlite opens it, avoiding
    # "unable to open database file" from aiosqlite's background thread.
    try:
        Path("/tmp").mkdir(parents=True, exist_ok=True)
        _pre = sqlite3.connect(DB_PATH)
        _pre.close()
    except Exception as _e:
        print(f"[session] pre-create DB warning: {_e}")

    # NullPool: no connection pool — each async operation gets a fresh
    # DBAPI connection and releases it immediately. Required on serverless
    # where long-lived pooled connections cause issues.
    engine = create_async_engine(
        db_url,
        echo=(settings.APP_ENV == "development"),
        future=True,
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
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
