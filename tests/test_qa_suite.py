import io
import pytest
from httpx import AsyncClient

from tests.conftest import login


# ==============================================================================
# 1. AUTHENTICATION & SESSION LIFECYCLE QA TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_auth_registration_validation(client: AsyncClient):
    """QA Test: Ensure registration rejects missing mandatory fields."""
    # Missing device_id and device_platform
    resp = await client.post(
        "/auth/verify-otp",
        json={"email": "incomplete@example.com"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert len(body["error"]["details"]) > 0


@pytest.mark.asyncio
async def test_auth_unauthenticated_access_rejection(client: AsyncClient):
    """QA Test: Protected endpoints strictly reject unauthenticated requests."""
    protected_endpoints = [
        ("GET", "/user/me"),
        ("GET", "/dashboard/home"),
        ("GET", "/feed/pinned"),
        ("GET", "/memories"),
        ("GET", "/chat/messages"),
        ("GET", "/graph"),
        ("GET", "/clusters"),
        ("GET", "/events"),
        ("GET", "/nudges"),
    ]
    for method, path in protected_endpoints:
        resp = await client.request(method, path)
        assert resp.status_code == 401, f"{method} {path} should return 401"
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] in ("UNAUTHORIZED", "HTTP_ERROR")


@pytest.mark.asyncio
async def test_auth_invalid_token_format(client: AsyncClient):
    """QA Test: Malformed or forged Bearer tokens are rejected."""
    resp = await client.get("/user/me", headers={"Authorization": "Bearer not-a-valid-jwt-token"})
    assert resp.status_code == 401
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] in ("TOKEN_INVALID", "UNAUTHORIZED")


@pytest.mark.asyncio
async def test_auth_device_update(client: AsyncClient, auth_headers: dict):
    """QA Test: User can update device tokens (PUT /auth/device)."""
    resp = await client.put(
        "/auth/device",
        headers=auth_headers,
        json={"fcm_token": "updated-fcm-9999", "device_platform": "ios"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["updated"] is True


@pytest.mark.asyncio
async def test_auth_logout_all_sessions(client: AsyncClient, auth_headers: dict):
    """QA Test: Logout all invalidates token generation."""
    resp = await client.post("/auth/logout_all", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["sessions_revoked"] >= 1

    # Immediate subsequent request using the invalidated token should be rejected (401)
    me_resp = await client.get("/user/me", headers=auth_headers)
    assert me_resp.status_code == 401


# ==============================================================================
# 2. USER PROFILE, PREFERENCES & GDPR DATA QA TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_user_preferences_lifecycle(client: AsyncClient, auth_headers: dict):
    """QA Test: Updating user preferences via PATCH."""
    patch_resp = await client.patch(
        "/user/preferences",
        headers=auth_headers,
        json={
            "timezone": "Asia/Kolkata",
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "07:00",
            "sunday_digest_enabled": True,
            "nudges_per_day": 3,
        },
    )
    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert body["success"] is True
    assert body["data"]["timezone"] == "Asia/Kolkata"
    assert body["data"]["nudges_per_day"] == 3


@pytest.mark.asyncio
async def test_user_export_and_status(client: AsyncClient, auth_headers: dict):
    """QA Test: Requesting GDPR data export and checking status."""
    req_resp = await client.post("/user/export", headers=auth_headers)
    assert req_resp.status_code == 202
    req_body = req_resp.json()
    assert req_body["success"] is True
    export_id = req_body["data"]["export_id"]

    # Poll status
    status_resp = await client.get(f"/user/export/{export_id}", headers=auth_headers)
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["success"] is True
    assert status_body["data"]["status"] == "ready"
    assert "download_url" in status_body["data"]


@pytest.mark.asyncio
async def test_user_delete_data_negative_validation(client: AsyncClient, auth_headers: dict):
    """QA Test: Deletion requires exact string 'DELETE MY DATA'."""
    resp = await client.request(
        "DELETE",
        "/user/data",
        headers=auth_headers,
        json={"confirmation": "please delete me"},
    )
    assert resp.status_code in (400, 422)
    body = resp.json()
    assert body["success"] is False


# ==============================================================================
# 3. FEED, MEMORIES, DASHBOARD & FILES QA TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_dashboard_home_endpoint(client: AsyncClient, auth_headers: dict):
    """QA Test: GET /dashboard/home returns profile, recommendations and counts."""
    resp = await client.get("/dashboard/home", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "profile" in body["data"]
    assert "recommendations" in body["data"]
    assert "unread_notifications_count" in body["data"]


@pytest.mark.asyncio
async def test_feed_pinned_endpoint(client: AsyncClient, auth_headers: dict):
    """QA Test: GET /feed/pinned returns list of pinned items."""
    resp = await client.get("/feed/pinned", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "items" in body["data"]
    assert isinstance(body["data"]["items"], list)
    if body["data"]["items"]:
        item = body["data"]["items"][0]
        assert "id" in item
        assert "title" in item
        assert item["is_pinned"] is True


@pytest.mark.asyncio
async def test_memories_endpoints(client: AsyncClient, auth_headers: dict):
    """QA Test: Memory list, save memory, and memories graph."""
    # 1. List
    list_resp = await client.get("/memories", headers=auth_headers)
    assert list_resp.status_code == 200
    list_body = list_resp.json()
    assert list_body["success"] is True
    assert "memories" in list_body["data"]

    # 2. Save
    save_resp = await client.post("/memories/mem_001/save", headers=auth_headers)
    assert save_resp.status_code == 200
    save_body = save_resp.json()
    assert save_body["success"] is True
    assert save_body["data"]["is_saved"] is True

    # 3. Graph
    graph_resp = await client.get("/memories/graph", headers=auth_headers)
    assert graph_resp.status_code == 200
    graph_body = graph_resp.json()
    assert graph_body["success"] is True
    assert "nodes" in graph_body["data"]
    assert "edges" in graph_body["data"]


@pytest.mark.asyncio
async def test_files_hierarchy_endpoint(client: AsyncClient, auth_headers: dict):
    """QA Test: GET /files returns folders and files hierarchy."""
    resp = await client.get("/files", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "folders" in body["data"]
    assert "files" in body["data"]


@pytest.mark.asyncio
async def test_notifications_lifecycle(client: AsyncClient, auth_headers: dict):
    """QA Test: GET /notifications and mark all as read."""
    get_resp = await client.get("/notifications", headers=auth_headers)
    assert get_resp.status_code == 200
    get_body = get_resp.json()
    assert get_body["success"] is True
    assert "unread_count" in get_body["data"]

    mark_resp = await client.patch("/notifications/mark-read", headers=auth_headers)
    assert mark_resp.status_code == 200
    assert mark_resp.json()["data"]["updated"] is True


# ==============================================================================
# 4. CHAT & VOICE PIPELINE QA TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_chat_audio_transcription(client: AsyncClient, auth_headers: dict):
    """QA Test: Uploading voice note for transcription."""
    audio_content = b"RIFF....WAVEfmt ...."
    files = {"file": ("voicenote.wav", io.BytesIO(audio_content), "audio/wav")}

    resp = await client.post("/chat/transcribe", headers=auth_headers, files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "transcription" in body["data"]
    assert "ai_response" in body["data"]


@pytest.mark.asyncio
async def test_chat_branch_negative_foreign_parent(client: AsyncClient, auth_headers: dict):
    """QA Test: Branching from non-existent parent message returns 404."""
    resp = await client.post(
        "/chat/messages/branch",
        headers=auth_headers,
        json={
            "parent_message_id": "00000000-0000-0000-0000-000000000000",
            "content": "Trying to branch from nowhere",
            "language": "en",
            "input_mode": "text",
            "client_message_id": "client-uuid-branch-fail",
        },
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "ENTITY_NOT_FOUND"


# ==============================================================================
# 5. GRAPH, CLUSTERS & IDOR SECURITY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_multi_user_cluster_idor_isolation(client: AsyncClient):
    """QA Test (Security/IDOR): User B cannot view, modify, or delete User A's cluster."""
    token_a = (await login(client, "alpha@example.com", "device-alpha-123"))["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    token_b = (await login(client, "beta@example.com", "device-beta-456"))["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates a cluster
    create_resp = await client.post(
        "/clusters",
        headers=headers_a,
        json={"label": "Alpha Confidential Project", "color_accent": "#FF0000"},
    )
    assert create_resp.status_code == 201
    cluster_id = create_resp.json()["data"]["cluster_id"]

    # User B attempts to GET User A's cluster
    get_resp = await client.get(f"/clusters/{cluster_id}", headers=headers_b)
    assert get_resp.status_code == 404
    assert get_resp.json()["error"]["code"] == "ENTITY_NOT_FOUND"

    # User B attempts to PATCH User A's cluster
    patch_resp = await client.patch(
        f"/clusters/{cluster_id}",
        headers=headers_b,
        json={"label": "Hacked Cluster"},
    )
    assert patch_resp.status_code == 404

    # User B attempts to DELETE User A's cluster
    del_resp = await client.delete(f"/clusters/{cluster_id}", headers=headers_b)
    assert del_resp.status_code == 404


# ==============================================================================
# 6. BRIEFING, SEARCH & DIGEST QA TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_briefing_parameter_validation(client: AsyncClient, auth_headers: dict):
    """QA Test: GET /briefing requires query or node_id."""
    resp = await client.get("/briefing", headers=auth_headers)
    assert resp.status_code in (400, 422)
    body = resp.json()
    assert body["success"] is False


@pytest.mark.asyncio
async def test_search_endpoint_and_sanitization(client: AsyncClient, auth_headers: dict):
    """QA Test: POST /search handles semantic search and sanitization."""
    resp = await client.post(
        "/search",
        headers=auth_headers,
        json={"query": "career advice and job offer", "limit": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "items" in body["data"]
    assert "pagination" in body["data"]


@pytest.mark.asyncio
async def test_weekly_digest_endpoint(client: AsyncClient, auth_headers: dict):
    """QA Test: GET /digest/weekly returns aggregated stats."""
    resp = await client.get("/digest/weekly", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "stats" in body["data"]


# ==============================================================================
# 7. BOUNDARY, SANITIZATION & FAANG ENVELOPE AUDIT
# ==============================================================================

@pytest.mark.asyncio
async def test_boundary_validation_nudges_per_day(client: AsyncClient, auth_headers: dict):
    """QA Test: Boundary check - nudges_per_day > 5 must trigger validation error."""
    resp = await client.patch(
        "/user/preferences",
        headers=auth_headers,
        json={"nudges_per_day": 999},  # Max allowed is 5
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_sql_injection_resilience(client: AsyncClient, auth_headers: dict):
    """QA Test: SQL Injection characters in search are sanitized safely."""
    sqli_payload = "'; DROP TABLE users; SELECT * FROM nodes WHERE '1'='1"
    resp = await client.post(
        "/search",
        headers=auth_headers,
        json={"query": sqli_payload, "limit": 3},
    )
    # Must succeed cleanly without DB syntax crash or 500 error
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


@pytest.mark.asyncio
async def test_non_existent_route_envelope_compliance(client: AsyncClient):
    """QA Test: 404 responses conform to FAANG envelope specification."""
    resp = await client.get("/non-existent-endpoint-xyz")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["data"] is None
    assert "error" in body
    assert body["error"]["code"] == "ENTITY_NOT_FOUND"
    assert "timestamp" in body
