import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_send_and_branch_message(client: AsyncClient, auth_headers: dict):
    # 1. Send root message
    resp = await client.post(
        "/chat/messages",
        headers=auth_headers,
        json={
            "content": "Had a long call with Rahul today. He got the job offer.",
            "language": "en",
            "input_mode": "text",
            "session_date": "2026-07-06",
            "client_message_id": "client-uuid-1",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "success"
    assert "Rahul" in body["data"]["message"]["content"]
    assert body["data"]["ai_response"]["content"] != ""
    assert len(body["data"]["ai_response"]["suggested_replies"]) > 0

    parent_id = body["data"]["message"]["message_id"]

    # 2. Branch message
    branch_resp = await client.post(
        "/chat/messages/branch",
        headers=auth_headers,
        json={
            "parent_message_id": parent_id,
            "content": "Don't want to cook tonight",
            "language": "en",
            "input_mode": "text",
            "client_message_id": "client-uuid-2",
        },
    )
    assert branch_resp.status_code == 201
    branch_body = branch_resp.json()
    assert branch_body["data"]["message"]["branch_depth"] == 1

    # 3. Fetch message thread
    thread_resp = await client.get("/chat/messages", headers=auth_headers)
    assert thread_resp.status_code == 200
    assert len(thread_resp.json()["data"]["items"]) >= 2
