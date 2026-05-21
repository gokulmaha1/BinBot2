import json
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)
            for conn in disconnected:
                self.active_connections[user_id].discard(conn)

    async def broadcast(self, message: dict):
        for user_id in self.active_connections:
            await self.send_personal(message, user_id)


manager = ConnectionManager()


@router.websocket("/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


async def send_trade_update(user_id: str, trade_data: dict):
    await manager.send_personal({
        "type": "trade_update",
        "data": trade_data,
    }, user_id)


async def send_bot_update(user_id: str, bot_data: dict):
    await manager.send_personal({
        "type": "bot_update",
        "data": bot_data,
    }, user_id)


async def send_market_update(user_id: str, market_data: dict):
    await manager.send_personal({
        "type": "market_update",
        "data": market_data,
    }, user_id)
