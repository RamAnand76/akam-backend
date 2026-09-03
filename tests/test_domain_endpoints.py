import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_graph_endpoints(client: AsyncClient, auth_headers: dict):
    # 1. Fetch graph
    resp = await client.get("/graph", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert "nodes" in body["data"]
    assert "edges" in body["data"]


@pytest.mark.asyncio
async def test_cluster_endpoints(client: AsyncClient, auth_headers: dict):
    # 1. Create manual cluster
    create_resp = await client.post(
        "/clusters",
        headers=auth_headers,
        json={"label": "Personal Development", "color_accent": "#8B5CF6"},
    )
    assert create_resp.status_code == 201
    c_data = create_resp.json()["data"]
    cluster_id = c_data["cluster_id"]

    # 2. Get clusters
    list_resp = await client.get("/clusters", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]["items"]) >= 1

    # 3. Patch cluster
    patch_resp = await client.patch(
        f"/clusters/{cluster_id}",
        headers=auth_headers,
        json={"label": "Updated Career Cluster"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["label"] == "Updated Career Cluster"

    # 4. Delete cluster
    del_resp = await client.delete(f"/clusters/{cluster_id}", headers=auth_headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_event_and_panels(client: AsyncClient, auth_headers: dict):
    # 1. Create event
    ev_resp = await client.post(
        "/events",
        headers=auth_headers,
        json={
            "title": "Weekend Retreat",
            "emoji": "🌲",
            "date_start": "2026-10-15",
            "date_end": "2026-10-18",
            "panels": [
                {
                    "type": "plans",
                    "label": "Packing List",
                    "items": [{"text": "Hiking boots"}, {"text": "Rain jacket"}],
                }
            ],
        },
    )
    assert ev_resp.status_code == 201
    event = ev_resp.json()["data"]
    event_id = event["event_id"]
    panel_id = event["panels"][0]["panel_id"]

    # 2. Add panel item
    add_item = await client.post(
        f"/events/{event_id}/panels/{panel_id}/items",
        headers=auth_headers,
        json={"text": "Water bottle", "done": False},
    )
    assert add_item.status_code == 201
    item_id = add_item.json()["data"]["item_id"]

    # 3. Toggle panel item
    patch_item = await client.patch(
        f"/events/{event_id}/panels/{panel_id}/items/{item_id}",
        headers=auth_headers,
        json={"done": True},
    )
    assert patch_item.status_code == 200
    assert patch_item.json()["data"]["done"] is True


@pytest.mark.asyncio
async def test_nudges_and_screentime(client: AsyncClient, auth_headers: dict):
    # 1. Fetch nudges
    nudges_resp = await client.get("/nudges", headers=auth_headers)
    assert nudges_resp.status_code == 200

    # 2. Trigger screentime warning
    st_resp = await client.post(
        "/nudges/screentime",
        headers=auth_headers,
        json={
            "date": "2026-07-06",
            "total_minutes": 320,
            "social_media_minutes": 150,
            "akam_minutes": 20,
            "app_breakdown": [{"app_name": "Instagram", "minutes": 90}],
        },
    )
    assert st_resp.status_code == 200
    assert st_resp.json()["data"]["nudge_triggered"] is True
    nudge_id = st_resp.json()["data"]["nudge_id"]

    # 3. Take action on nudge
    action_resp = await client.post(
        f"/nudges/{nudge_id}/action",
        headers=auth_headers,
        json={"action": "cta_primary"},
    )
    assert action_resp.status_code == 200
    assert action_resp.json()["data"]["recorded"] is True


@pytest.mark.asyncio
async def test_user_profile_and_deletion(client: AsyncClient, auth_headers: dict):
    # 1. Get profile
    me_resp = await client.get("/user/me", headers=auth_headers)
    assert me_resp.status_code == 200
    assert "graph_stats" in me_resp.json()["data"]

    # 2. Patch user
    patch_resp = await client.patch(
        "/user/me",
        headers=auth_headers,
        json={"name": "New Name", "language": "ml"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["name"] == "New Name"

    # 3. Permanent delete user data with confirmation
    del_resp = await client.request(
        "DELETE",
        "/user/data",
        headers=auth_headers,
        json={"confirmation": "DELETE MY DATA"},
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["status"] == "initiated"
