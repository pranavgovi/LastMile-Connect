"""Connection manager for real-time WebSocket updates (sessions, intents). Avoids circular imports."""
import asyncio
import json
from typing import Set

from fastapi import WebSocket


class UpdatesConnectionManager:
    """Maps user_id -> set of WebSockets. Notify users when their sessions or intents change."""

    def __init__(self) -> None:
        self._connections: dict[int, Set[WebSocket]] = {}

    def connect(self, user_id: int, websocket: WebSocket) -> None:
        if user_id not in self._connections:
            self._connections[user_id] = set()
        self._connections[user_id].add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        if user_id in self._connections:
            self._connections[user_id].discard(websocket)
            if not self._connections[user_id]:
                del self._connections[user_id]

    async def notify_user(self, user_id: int, message: dict) -> None:
        if user_id not in self._connections:
            return
        text = json.dumps(message)
        dead = set()
        for ws in self._connections[user_id]:
            try:
                await ws.send_text(text)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._connections[user_id].discard(ws)
        if user_id in self._connections and not self._connections[user_id]:
            del self._connections[user_id]

    async def notify_users(self, user_ids: list[int], message: dict) -> None:
        await asyncio.gather(*[self.notify_user(uid, message) for uid in user_ids])


updates_manager = UpdatesConnectionManager()
