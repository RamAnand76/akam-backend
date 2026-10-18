from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

_url = settings.async_database_url
_kwargs: dict = {"echo": False, "future": True}
if _url.startswith("postgresql"):
    # NullPool + no prepared-statement cache: safe on serverless and behind Supabase's pgbouncer.
    _kwargs.update(poolclass=NullPool, connect_args={"statement_cache_size": 0})

engine = create_async_engine(_url, **_kwargs)

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
