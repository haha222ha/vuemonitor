import json
import uuid
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].close(code=4002)
            except Exception:
                pass
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, message: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(user_id)

    async def broadcast(self, message: dict):
        disconnected = []
        for uid, ws in self.active_connections.items():
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(uid)
        for uid in disconnected:
            self.disconnect(uid)


manager = ConnectionManager()

WS_MESSAGE_TYPES = [
    "collect:progress",
    "collect:completed",
    "collect:risk_alert",
    "monitor:triggered",
    "ai:analysis_done",
    "notification:new",
    "sync:push",
    "sync:pull",
]

_WS_IDLE_TIMEOUT = 300


async def _ws_heartbeat(websocket: WebSocket, user_id: str):
    while True:
        await asyncio.sleep(_WS_IDLE_TIMEOUT)
        try:
            await websocket.send_json({"type": "ping", "ts": datetime.now(timezone.utc).isoformat()})
        except Exception:
            manager.disconnect(user_id)
            break


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await manager.connect(user_id, websocket)
    heartbeat_task = asyncio.create_task(_ws_heartbeat(websocket, user_id))
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")
                if msg_type == "pong":
                    pass
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong", "ts": datetime.now(timezone.utc).isoformat()})
                elif msg_type == "sync:pull":
                    await websocket.send_json({
                        "type": "sync:pull_response",
                        "data": msg.get("data", {}),
                        "ts": datetime.now(timezone.utc).isoformat(),
                    })
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    finally:
        heartbeat_task.cancel()
