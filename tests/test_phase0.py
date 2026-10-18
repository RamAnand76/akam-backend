import subprocess
import sys

import pytest
import structlog
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.config import Settings, settings
from app.main import app
from tests.conftest import login

PROD = dict(
    APP_ENV="production",
    DATABASE_URL="postgresql://u:p@db.example.com:5432/akam",
    JWT_PRIVATE_KEY="priv",
    JWT_PUBLIC_KEY="pub",
    OTP_HASH_SECRET="pepper",
    EMAIL_BACKEND="resend",
    RESEND_API_KEY="re_test",
    ALLOWED_ORIGINS="https://app.akam.app",
)


def make(**over) -> Settings:
    return Settings(_env_file=None, **{**PROD, **over})


# ── 1. Config ────────────────────────────────────────────────────────────────
def test_production_settings_valid_and_url_normalised():
    s = make()
    assert s.async_database_url == "postgresql+asyncpg://u:p@db.example.com:5432/akam"
    assert s.ACCESS_TOKEN_TTL_SECONDS == 3600 and s.REFRESH_TOKEN_TTL_SECONDS == 2592000


@pytest.mark.parametrize("missing", ["DATABASE_URL", "JWT_PRIVATE_KEY", "JWT_PUBLIC_KEY", "OTP_HASH_SECRET"])
@pytest.mark.parametrize("env", ["staging", "production"])
def test_deployed_envs_fail_fast_on_missing_secret(missing, env):
    with pytest.raises(ValidationError):
        make(APP_ENV=env, **{missing: ""})


def test_deployed_rejects_console_email_and_sqlite():
    with pytest.raises(ValidationError):
        make(EMAIL_BACKEND="console")
    with pytest.raises(ValidationError):
        make(DATABASE_URL="sqlite+aiosqlite:///x.db")


def test_cors_wildcard_rejected_everywhere():
    for env in ("development", "production"):
        with pytest.raises(ValidationError):
            make(APP_ENV=env, ALLOWED_ORIGINS="*")


def test_no_default_jwt_secret_and_dev_requires_database_url():
    assert not hasattr(Settings, "JWT_SECRET_KEY") and "JWT_SECRET_KEY" not in Settings.model_fields
    with pytest.raises(ValidationError):
        Settings(_env_file=None, APP_ENV="development", DATABASE_URL="")


def test_jwt_keys_must_be_paired_and_model_settings_validated():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, DATABASE_URL="sqlite+aiosqlite:///:memory:", JWT_PRIVATE_KEY="x")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, DATABASE_URL="sqlite+aiosqlite:///:memory:", MODEL_VERSION="1", MODEL_URL="https://x", MODEL_SHA256="abc")


async def test_cors_allow_list_enforced(client: AsyncClient):
    ok = await client.options("/auth/request-otp", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = await client.options("/auth/request-otp", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in bad.headers


def test_env_example_lists_every_setting_without_secrets():
    text = open(".env.example", encoding="utf-8").read()
    for name in Settings.model_fields:
        assert f"{name}=" in text, name
    assert "BEGIN" not in text


# ── 2. Database / migrations ─────────────────────────────────────────────────
def test_alembic_upgrade_downgrade_and_no_model_drift(tmp_path):
    env = {**__import__("os").environ, "DATABASE_URL": f"sqlite+aiosqlite:///{tmp_path / 'm.db'}"}
    for args in (["upgrade", "head"], ["check"], ["downgrade", "base"], ["upgrade", "head"]):
        r = subprocess.run([sys.executable, "-m", "alembic", *args], env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr


# ── 4. Config endpoints ──────────────────────────────────────────────────────
async def test_models_manifest_404_when_unset(client: AsyncClient):
    r = await client.get("/config/models")
    assert r.status_code == 404
    assert r.json()["success"] is False and r.json()["error"]["code"] == "MODEL_MANIFEST_NOT_CONFIGURED"


async def test_models_manifest_returns_envelope(client: AsyncClient, monkeypatch):
    sha = "AB" * 32
    for k, v in dict(MODEL_VERSION="gemma-1", MODEL_URL="https://cdn.example/m.task", MODEL_SHA256=sha, MODEL_SIZE_BYTES=123).items():
        monkeypatch.setattr(settings, k, v)
    r = await client.get("/config/models")  # no auth header
    assert r.status_code == 200
    assert r.json()["data"] == {"version": "gemma-1", "url": "https://cdn.example/m.task", "sha256": sha.lower(), "size_bytes": 123}
    assert r.json()["success"] is True


async def test_app_config(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "MIN_APP_VERSION", "1.2.0")
    monkeypatch.setattr(settings, "FEATURE_FLAGS", '{"analytics": true}')
    r = await client.get("/config/app")
    assert r.json()["data"] == {"min_app_version": "1.2.0", "feature_flags": {"analytics": True}}


# ── 5. Hardening ─────────────────────────────────────────────────────────────
async def test_health_and_ready(client: AsyncClient):
    assert (await client.get("/health")).json()["data"]["status"] == "ok"
    assert (await client.get("/ready")).json()["data"]["status"] == "ready"


async def test_ready_503_when_db_down(client: AsyncClient, monkeypatch):
    class Broken:
        def __call__(self):
            raise RuntimeError("down")

    monkeypatch.setattr("app.routers.health.async_session_factory", Broken())
    r = await client.get("/ready")
    assert r.status_code == 503 and r.json()["error"]["code"] == "NOT_READY"


async def test_per_endpoint_rate_limit_by_ip(client: AsyncClient):
    codes = [(await client.post("/auth/refresh", json={})).status_code for _ in range(11)]
    assert codes[:10] == [422] * 10 and codes[10] == 429
    r = await client.post("/auth/refresh", json={})
    assert r.json()["success"] is False and r.json()["error"]["code"] == "RATE_LIMITED" and "Retry-After" in r.headers


async def test_rate_limit_keyed_by_user_not_ip(client: AsyncClient):
    a = await login(client, "ua@example.com", "device-ua-00001")
    b = await login(client, "ub@example.com", "device-ub-00002")
    ha, hb = ({"Authorization": f"Bearer {d['access_token']}"} for d in (a, b))
    assert (await client.post("/auth/logout_all", headers=ha)).status_code == 200
    # Same IP, same endpoint: B has its own budget (2/hour).
    assert (await client.post("/auth/logout_all", headers=hb)).status_code == 200


async def test_idempotency_scoped_by_user(client: AsyncClient):
    a = await login(client, "ia@example.com", "device-ia-00001")
    b1 = await login(client, "ib@example.com", "device-ib-00002")
    b2 = await login(client, "ib@example.com", "device-ib-00003")  # B now has 1 live session (b2) + replaced b1
    assert b2["user_id"] == b1["user_id"]
    key = {"Idempotency-Key": "same-key-123"}
    ra = await client.post("/auth/logout_all", headers={**key, "Authorization": f"Bearer {a['access_token']}"})
    assert ra.status_code == 200 and ra.json()["data"]["sessions_revoked"] == 1
    rb = await client.post("/auth/logout_all", headers={**key, "Authorization": f"Bearer {b2['access_token']}"})
    assert rb.status_code == 200 and "idempotent-replayed" not in rb.headers  # not A's cached response


async def test_unhandled_exception_logged_and_enveloped(async_db):
    async def boom():
        raise RuntimeError("kaboom")

    app.router.add_api_route("/api/v1/_boom", boom, methods=["GET"])
    try:
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            with structlog.testing.capture_logs() as logs:
                r = await ac.get("/api/v1/_boom")
    finally:
        app.router.routes.pop()
    assert r.status_code == 500 and r.json()["error"]["code"] == "INTERNAL_ERROR" and r.json()["success"] is False
    assert any(e["event"] == "unhandled_exception" and e["path"] == "/api/v1/_boom" for e in logs)


def test_content_endpoints_marked_deprecated_auth_not():
    paths = app.openapi()["paths"]
    assert paths["/api/v1/chat/messages"]["post"].get("deprecated") is True
    assert paths["/api/v1/graph"]["get"].get("deprecated") is True if "/api/v1/graph" in paths else True
    assert not paths["/api/v1/auth/request-otp"]["post"].get("deprecated")
    assert paths["/api/v1/auth/register"]["post"].get("deprecated") is True
    assert "/api/v1/config/models" in paths and "/api/v1/health" in paths
