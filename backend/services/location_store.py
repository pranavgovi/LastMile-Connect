"""Ephemeral location storage in Redis (TTL, no history)."""
import json
from typing import Any

from backend.config import settings


def _key(session_id: int) -> str:
    return f"session:{session_id}:locations"


async def set_location(redis: Any, session_id: int, party: str, lat: float, lng: float) -> None:
    """Write party's last location; merge with existing a/b. TTL on key."""
    key = _key(session_id)
    raw = await redis.get(key)
    data = json.loads(raw) if raw else {}
    data[party] = {"lat": lat, "lng": lng}
    await redis.setex(key, settings.SESSION_LOCATION_TTL_SECONDS, json.dumps(data))


async def get_locations(redis: Any, session_id: int) -> dict[str, dict[str, float]]:
    """Read current locations for both parties. Returns e.g. { \"a\": { lat, lng }, \"b\": { ... } }."""
    key = _key(session_id)
    raw = await redis.get(key)
    if not raw:
        return {}
    return json.loads(raw)
