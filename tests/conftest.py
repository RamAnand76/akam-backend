import os

# Must be set before `app` is imported: settings are read at import time and env beats any local .env.
os.environ.update(
    APP_ENV="development",
    DATABASE_URL="sqlite+aiosqlite:///:memory:",
    JWT_PRIVATE_KEY="",
    JWT_PUBLIC_KEY="",
    OTP_HASH_SECRET="test-pepper",
    EMAIL_BACKEND="console",
    ENABLE_LEGACY_REGISTER="false",
    MODEL_VERSION="",
    MODEL_URL="",
    MODEL_SHA256="",
    ALLOWED_ORIGINS="http://localhost:3000",
)

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.dependencies import get_db
from app.main import app
from app.middleware.rate_limit import rate_limiter
from app.services.email_service import get_email_sender

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, future=True)
TestingSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


class OutboxSender:
    """Captures OTP emails instead of sending them."""

    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    async def send_otp(self, to: str, code: str, ttl_minutes: int) -> None:
        self.sent.append((to, code))

    def last_code(self, to: str) -> str:
        return [c for t, c in self.sent if t == to][-1]


@pytest_asyncio.fixture(scope="function")
async def async_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def outbox():
    return OutboxSender()


@pytest_asyncio.fixture(scope="function")
async def client(async_db, outbox):
    async def override_get_db():
        yield async_db

    rate_limiter.clear()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_sender] = lambda: outbox
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as ac:
        ac.outbox = outbox
        yield ac
    app.dependency_overrides.clear()


async def login(client: AsyncClient, email: str = "tester@example.com", device_id: str = "test-device-12345") -> dict:
    """Full OTP flow; returns the verify-otp `data` dict."""
    r = await client.post("/auth/request-otp", json={"email": email, "device_id": device_id})
    assert r.status_code == 200, r.text
    r = await client.post(
        "/auth/verify-otp",
        json={"email": email, "code": client.outbox.last_code(email), "device_id": device_id},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient):
    data = await login(client)
    return {"Authorization": f"Bearer {data['access_token']}"}
