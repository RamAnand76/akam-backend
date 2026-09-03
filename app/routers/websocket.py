import json
import uuid
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.security.jwt import verify_token

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id] = [
                ws for ws in self.active_connections[user_id] if ws != websocket
            ]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_text(json.dumps(message))

    async def broadcast_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_text(json.dumps(message))


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None):
    if not token:
        await websocket.close(code=4001, reason="token_missing")
        return

    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
    except Exception:
        await websocket.close(code=4001, reason="token_invalid")
        return

    await manager.connect(websocket, user_id)
    conn_id = str(uuid.uuid4())

    # Send connection_established event
    await manager.send_personal_message(
        {
            "type": "connection_established",
            "connection_id": conn_id,
            "server_time": datetime.utcnow().isoformat() + "Z",
            "rate_limit": {"messages_per_min": 60},
        },
        websocket,
    )

    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                event = json.loads(data_text)
            except Exception:
                continue

            event_type = event.get("type")
            if event_type == "ping":
                await manager.send_personal_message({"type": "pong", "server_time": datetime.utcnow().isoformat() + "Z"}, websocket)
            elif event_type == "token_refresh":
                new_token = event.get("access_token")
                try:
                    verify_token(new_token)
                except Exception:
                    await websocket.close(code=4001, reason="token_expired")
                    break
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
