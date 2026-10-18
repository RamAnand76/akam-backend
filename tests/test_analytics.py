import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.models.db.analytics import AnalyticsEvent


@pytest.mark.asyncio
async def test_analytics_ingest_happy_path(client: AsyncClient, auth_headers: dict, async_db):
    """Positive test: Ingesting a valid batch of allow-listed events."""
    resp = await client.post(
        "/analytics/events",
        headers=auth_headers,
        json={
            "anon_id": "anon-device-uuid-9999",
            "app_version": "1.0.0",
            "events": [
                {
                    "name": "screen_view",
                    "ts": "2026-10-18T12:00:00Z",
                    "props": {"screen": "home"},
                },
                {
                    "name": "model_download_completed",
                    "ts": "2026-10-18T12:05:00Z",
                    "props": {"duration_ms": 14200, "is_success": True},
                },
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["accepted"] == 2

    # Verify database persistence & absolute lack of user identity linkage
    db_events = (await async_db.execute(select(AnalyticsEvent))).scalars().all()
    assert len(db_events) == 2
    for ev in db_events:
        assert ev.anon_id == "anon-device-uuid-9999"
        assert not hasattr(ev, "user_id")
        assert not hasattr(ev, "email")


@pytest.mark.asyncio
async def test_analytics_unauthenticated_rejected(client: AsyncClient):
    """Security test: Analytics endpoint requires authentication."""
    resp = await client.post(
        "/analytics/events",
        json={
            "anon_id": "anon-device-uuid-9999",
            "app_version": "1.0.0",
            "events": [{"name": "screen_view", "ts": "2026-10-18T12:00:00Z", "props": {}}],
        },
    )
    assert resp.status_code == 401
    assert resp.json()["success"] is False


@pytest.mark.asyncio
async def test_analytics_forbidden_event_name_rejected(client: AsyncClient, auth_headers: dict):
    """Privacy test: Non-allow-listed event names are rejected with 422."""
    resp = await client.post(
        "/analytics/events",
        headers=auth_headers,
        json={
            "anon_id": "anon-device-uuid-9999",
            "app_version": "1.0.0",
            "events": [
                {
                    "name": "user_typed_secret_message",
                    "ts": "2026-10-18T12:00:00Z",
                    "props": {},
                }
            ],
        },
    )
    assert resp.status_code == 422
    assert resp.json()["success"] is False


@pytest.mark.asyncio
async def test_analytics_forbidden_prop_keys_rejected(client: AsyncClient, auth_headers: dict):
    """Privacy test: Free-text property keys like 'text', 'message', 'name' are rejected."""
    for bad_prop in ("text", "message", "query", "user_name", "email", "secret"):
        resp = await client.post(
            "/analytics/events",
            headers=auth_headers,
            json={
                "anon_id": "anon-device-uuid-9999",
                "app_version": "1.0.0",
                "events": [
                    {
                        "name": "screen_view",
                        "ts": "2026-10-18T12:00:00Z",
                        "props": {bad_prop: "some text content"},
                    }
                ],
            },
        )
        assert resp.status_code == 422, f"Property '{bad_prop}' should have been rejected with 422"
        assert resp.json()["success"] is False


@pytest.mark.asyncio
async def test_analytics_string_length_exceeded_rejected(client: AsyncClient, auth_headers: dict):
    """Privacy test: String property values over 40 characters are rejected with 422."""
    long_string = "a" * 41  # exceeds 40 chars
    resp = await client.post(
        "/analytics/events",
        headers=auth_headers,
        json={
            "anon_id": "anon-device-uuid-9999",
            "app_version": "1.0.0",
            "events": [
                {
                    "name": "screen_view",
                    "ts": "2026-10-18T12:00:00Z",
                    "props": {"screen": long_string},
                }
            ],
        },
    )
    assert resp.status_code == 422
    assert resp.json()["success"] is False


@pytest.mark.asyncio
async def test_analytics_batch_size_limit(client: AsyncClient, auth_headers: dict):
    """Boundary test: More than 100 events in a batch must be rejected."""
    events = [
        {"name": "screen_view", "ts": "2026-10-18T12:00:00Z", "props": {"screen": "home"}}
        for _ in range(101)
    ]
    resp = await client.post(
        "/analytics/events",
        headers=auth_headers,
        json={
            "anon_id": "anon-device-uuid-9999",
            "app_version": "1.0.0",
            "events": events,
        },
    )
    assert resp.status_code == 422
    assert resp.json()["success"] is False
