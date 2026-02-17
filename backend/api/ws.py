"""WebSocket: live location for ACTIVE sessions; real-time updates channel for sessions/intents."""
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.jwt import decode_token
from backend.database import async_session
from backend.models.session import Session, SessionState
from backend.redis_client import get_redis
from backend.services.location_store import set_location
from backend.services.ws_updates import updates_manager

router = APIRouter(tags=["ws"])


@router.websocket("/ws/sessions/{session_id}")
async def session_location_ws(websocket: WebSocket, session_id: int):
    """Accept connection with query ?token=...; session must be ACTIVE. Receive { lat, lng } and store in Redis."""
    await websocket.accept()
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4000)
        return
    async with async_session() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
    if not session or session.state != SessionState.ACTIVE:
        await websocket.close(code=4001)
        return
    if token not in (session.token_a, session.token_b):
        await websocket.close(code=4002)
        return
    party = "a" if token == session.token_a else "b"
    redis = await get_redis()
    try:
        while True:
            data = await websocket.receive_text()
            try:
                obj = json.loads(data)
                lat = float(obj.get("lat", 0))
                lng = float(obj.get("lng", 0))
                await set_location(redis, session_id, party, lat, lng)
            except (KeyError, TypeError, ValueError):
                pass
    except WebSocketDisconnect:
        pass


@router.websocket("/ws/updates")
async def updates_ws(websocket: WebSocket):
    """Connect with ?token=JWT. Server pushes { type: 'sessions' } or { type: 'intents' } when data changes."""
    await websocket.accept()
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4000)
        return
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        await websocket.close(code=4001)
        return
    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        await websocket.close(code=4001)
        return
    updates_manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        updates_manager.disconnect(user_id, websocket)
