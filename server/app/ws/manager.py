import json
import uuid
import asyncio
import zlib
import time
from datetime import datetime, timezone
from collections import deque

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token

router = APIRouter()

_WS_IDLE_TIMEOUT = 30
_WS_MAX_BUFFER_SIZE = 1000
_WS_COMPRESS_THRESHOLD = 512


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.message_buffers: dict[str, deque] = {}
        self.last_seen: dict[str, float] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].close(code=4002)
            except Exception:
                pass
        self.active_connections[user_id] = websocket
        self.last_seen[user_id] = time.time()

        if user_id in self.message_buffers:
            buffer = self.message_buffers[user_id]
            while buffer:
                msg = buffer.popleft()
                try:
                    await websocket.send_json(msg)
                except Exception:
                    buffer.appendleft(msg)
                    break

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)
        self.last_seen.pop(user_id, None)

    def _ensure_buffer(self, user_id: str):
        if user_id not in self.message_buffers:
            self.message_buffers[user_id] = deque(maxlen=_WS_MAX_BUFFER_SIZE)

    async def send_to_user(self, user_id: str, message: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                payload = json.dumps(message, default=str)
                if len(payload) > _WS_COMPRESS_THRESHOLD:
                    compressed = zlib.compress(payload.encode("utf-8"))
                    await ws.send_bytes(compressed)
                else:
                    await ws.send_json(message)
                self.last_seen[user_id] = time.time()
            except Exception:
                self.disconnect(user_id)
                self._ensure_buffer(user_id)
                self.message_buffers[user_id].append(message)
        else:
            self._ensure_buffer(user_id)
            self.message_buffers[user_id].append(message)

    async def broadcast(self, message: dict):
        disconnected = []
        for uid, ws in self.active_connections.items():
            try:
                payload = json.dumps(message, default=str)
                if len(payload) > _WS_COMPRESS_THRESHOLD:
                    compressed = zlib.compress(payload.encode("utf-8"))
                    await ws.send_bytes(compressed)
                else:
                    await ws.send_json(message)
            except Exception:
                disconnected.append(uid)
        for uid in disconnected:
            self.disconnect(uid)
            self._ensure_buffer(uid)
            self.message_buffers[uid].append(message)

    def get_buffered_count(self, user_id: str) -> int:
        buf = self.message_buffers.get(user_id)
        return len(buf) if buf else 0

    def get_connection_stats(self) -> dict:
        return {
            "active_connections": len(self.active_connections),
            "buffered_users": sum(1 for buf in self.message_buffers.values() if len(buf) > 0),
            "total_buffered": sum(len(buf) for buf in self.message_buffers.values()),
        }


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


async def _ws_heartbeat(websocket: WebSocket, user_id: str):
    missed_pings = 0
    max_missed = 3
    while True:
        await asyncio.sleep(_WS_IDLE_TIMEOUT)
        if user_id not in manager.active_connections:
            break
        try:
            await websocket.send_json({"type": "ping", "ts": datetime.now(timezone.utc).isoformat()})
            missed_pings += 1
            if missed_pings > max_missed:
                manager.disconnect(user_id)
                break
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
                    manager.last_seen[user_id] = time.time()
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
