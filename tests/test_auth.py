import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_refresh(client: AsyncClient):
    # 1. Register new user
    reg = await client.post(
        "/auth/register",
        json={
            "name": "Arjun Das",
            "language": "en",
            "device_id": "arjun-phone-987654",
            "fcm_token": "fcm-sample-token-abc",
            "device_platform": "android",
        },
    )
    assert reg.status_code == 201
    body = reg.json()
    assert body["status"] == "success"
    assert "access_token" in body["data"]
    assert "refresh_token" in body["data"]

    refresh_token = body["data"]["refresh_token"]

    # 2. Refresh tokens
    ref = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert ref.status_code == 200
    ref_body = ref.json()
    assert ref_body["status"] == "success"
    assert "access_token" in ref_body["data"]


@pytest.mark.asyncio
async def test_logout_and_logout_all(client: AsyncClient):
    reg = await client.post(
        "/auth/register",
        json={
            "name": "Dev User",
            "language": "en",
            "device_id": "dev-phone-112233",
            "fcm_token": "fcm-sample-dev",
            "device_platform": "ios",
        },
    )
    data = reg.json()["data"]
    headers = {"Authorization": f"Bearer {data['access_token']}"}

    # Logout
    logout_resp = await client.post(
        "/auth/logout",
        headers=headers,
        json={"refresh_token": data["refresh_token"]},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["data"]["revoked"] is True
