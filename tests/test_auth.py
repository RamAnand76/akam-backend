from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update

from app.config import settings
from app.models.db.auth import OtpCode
from tests.conftest import TestingSessionLocal, login

DEV = "test-device-12345"


async def _request(client, email="a@example.com", device=DEV):
    return await client.post("/auth/request-otp", json={"email": email, "device_id": device})


async def _verify(client, code, email="a@example.com", device=DEV):
    return await client.post("/auth/verify-otp", json={"email": email, "code": code, "device_id": device})


async def _refresh(client, data, token=None):
    return await client.post(
        "/auth/refresh",
        json={"refresh_token": token or data["refresh_token"], "device_secret": data["device_secret"]},
    )


@pytest.mark.asyncio
async def test_otp_login_flow_and_envelope(client: AsyncClient):
    r = await _request(client)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True and body["data"]["expires_in"] == 600 and "timestamp" in body

    data = await login(client, "b@example.com")
    assert data["is_new_user"] is True and data["device_secret"]
    assert data["expires_in"] == 3600 and data["refresh_expires_in"] == 2592000
    me = await client.get("/user/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200

    again = await login(client, "b@example.com", "other-device-98765")
    assert again["is_new_user"] is False and again["user_id"] == data["user_id"]


@pytest.mark.asyncio
async def test_otp_hashed_at_rest_and_email_normalised(client: AsyncClient, async_db):
    await _request(client, "MiXeD@Example.com")
    code = client.outbox.last_code("mixed@example.com")
    row = (await async_db.execute(select(OtpCode))).scalar_one()
    assert code not in row.code_hash and len(row.code_hash) == 64 and row.email == "mixed@example.com"
    assert len(code) == 6 and code.isdigit()


@pytest.mark.asyncio
async def test_wrong_code_attempts_lock_out_even_correct_code(client: AsyncClient):
    await _request(client)
    good = client.outbox.last_code("a@example.com")
    bad = "000000" if good != "000000" else "111111"
    for _ in range(5):
        r = await _verify(client, bad)
        assert r.status_code == 400 and r.json()["error"]["code"] == "OTP_INVALID"
    r = await _verify(client, good)
    assert r.status_code == 429 and r.json()["error"]["code"] == "OTP_ATTEMPTS_EXCEEDED"


@pytest.mark.asyncio
async def test_expired_and_reused_code_rejected(client: AsyncClient):
    await _request(client)
    code = client.outbox.last_code("a@example.com")
    async with TestingSessionLocal() as s:
        await s.execute(update(OtpCode).values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        await s.commit()
    assert (await _verify(client, code)).json()["error"]["code"] == "OTP_INVALID"

    await _request(client, "c@example.com")
    code = client.outbox.last_code("c@example.com")
    assert (await _verify(client, code, "c@example.com")).status_code == 200
    assert (await _verify(client, code, "c@example.com")).status_code == 400


@pytest.mark.asyncio
async def test_new_code_invalidates_old(client: AsyncClient):
    await _request(client)
    old = client.outbox.last_code("a@example.com")
    await _request(client)
    new = client.outbox.last_code("a@example.com")
    if old != new:
        assert (await _verify(client, old)).status_code == 400
    assert (await _verify(client, new)).status_code == 200


@pytest.mark.asyncio
async def test_request_otp_rate_limits_per_email_and_ip(client: AsyncClient, monkeypatch):
    for _ in range(settings.OTP_REQUESTS_PER_EMAIL):
        assert (await _request(client, "limit@example.com")).status_code == 200
    r = await _request(client, "limit@example.com")
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED"

    monkeypatch.setattr(settings, "OTP_REQUESTS_PER_IP", 4)  # 3 rows already from this IP
    assert (await _request(client, "x1@example.com")).status_code == 200
    assert (await _request(client, "x2@example.com")).status_code == 429


@pytest.mark.asyncio
async def test_email_send_failure_is_503(client: AsyncClient):
    from app.main import app
    from app.services.email_service import get_email_sender

    class Boom:
        async def send_otp(self, *a):
            raise RuntimeError("smtp down")

    app.dependency_overrides[get_email_sender] = lambda: Boom()
    r = await _request(client)
    assert r.status_code == 503 and r.json()["error"]["code"] == "EMAIL_SEND_FAILED"


@pytest.mark.asyncio
async def test_refresh_rotates_and_reuse_revokes_family(client: AsyncClient):
    data = await login(client)
    first = data["refresh_token"]
    r = await _refresh(client, data)
    assert r.status_code == 200
    new = r.json()["data"]
    assert new["refresh_token"] != first and new["expires_in"] == 3600

    # Replay of the rotated token: rejected and the whole family dies.
    r = await _refresh(client, data, first)
    assert r.status_code == 401 and r.json()["error"]["code"] == "TOKEN_REUSE_DETECTED"
    assert (await _refresh(client, data, new["refresh_token"])).json()["error"]["code"] == "TOKEN_REVOKED"
    me = await client.get("/user/me", headers={"Authorization": f"Bearer {new['access_token']}"})
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_refresh_requires_correct_device_secret(client: AsyncClient):
    data = await login(client)
    r = await client.post("/auth/refresh", json={"refresh_token": data["refresh_token"], "device_secret": "x" * 43})
    assert r.status_code == 401
    # A wrong secret must not burn the legitimate token.
    assert (await _refresh(client, data)).status_code == 200


@pytest.mark.asyncio
async def test_access_token_is_not_a_refresh_token(client: AsyncClient):
    data = await login(client)
    r = await _refresh(client, data, data["access_token"])
    assert r.status_code == 401 and r.json()["error"]["code"] == "TOKEN_INVALID"


@pytest.mark.asyncio
async def test_logout_revokes_session_tokens(client: AsyncClient):
    data = await login(client)
    h = {"Authorization": f"Bearer {data['access_token']}"}
    r = await client.post("/auth/logout", headers=h, json={"refresh_token": data["refresh_token"]})
    assert r.status_code == 200 and r.json()["data"]["revoked"] is True
    assert (await client.get("/user/me", headers=h)).status_code == 401
    assert (await _refresh(client, data)).json()["error"]["code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_logout_all_counts_real_sessions(client: AsyncClient):
    d1 = await login(client, "m@example.com", "phone-device-0001")
    d2 = await login(client, "m@example.com", "tablet-device-002")
    other = await login(client, "n@example.com", "other-device-0003")
    h1 = {"Authorization": f"Bearer {d1['access_token']}"}
    r = await client.post("/auth/logout_all", headers=h1)
    assert r.json()["data"]["sessions_revoked"] == 2
    assert (await client.get("/user/me", headers={"Authorization": f"Bearer {d2['access_token']}"})).status_code == 401
    assert (await client.get("/user/me", headers={"Authorization": f"Bearer {other['access_token']}"})).status_code == 200


@pytest.mark.asyncio
async def test_relogin_same_device_replaces_old_session(client: AsyncClient):
    old = await login(client)
    await login(client)
    assert (await client.get("/user/me", headers={"Authorization": f"Bearer {old['access_token']}"})).status_code == 401


@pytest.mark.asyncio
async def test_legacy_register_off_by_default_and_flag_on(client: AsyncClient, monkeypatch):
    payload = {"name": "Old", "device_id": "legacy-device-1", "fcm_token": "fcm-token-legacy-1"}
    r = await client.post("/auth/register", json=payload)
    assert r.status_code == 404
    monkeypatch.setattr(settings, "ENABLE_LEGACY_REGISTER", True)
    r = await client.post("/auth/register", json=payload)
    assert r.status_code == 201 and r.json()["data"]["expires_in"] == 3600


@pytest.mark.asyncio
async def test_update_device(client: AsyncClient, auth_headers):
    r = await client.put("/auth/device", headers=auth_headers, json={"fcm_token": "new-fcm-token-123", "device_platform": "ios"})
    assert r.status_code == 200 and r.json()["data"]["updated"] is True


@pytest.mark.asyncio
async def test_invalid_input_rejected(client: AsyncClient):
    assert (await client.post("/auth/request-otp", json={"email": "not-an-email", "device_id": DEV})).status_code == 422
    assert (await _verify(client, "12345")).status_code == 422
