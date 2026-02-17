"""OSRM client helpers for walking directions.

Uses the public OSRM demo server by default (fine for demos; not for production SLA).
"""

from __future__ import annotations

from typing import Any

import httpx


DEFAULT_OSRM_BASE_URL = "https://router.project-osrm.org"


def _format_instruction(maneuver: dict[str, Any], name: str | None) -> str:
    mtype = maneuver.get("type") or "continue"
    modifier = maneuver.get("modifier")
    road = (name or "").strip()
    if mtype == "depart":
        return f"Depart onto {road}" if road else "Depart"
    if mtype == "arrive":
        return "Arrive at destination"
    if mtype == "roundabout":
        return f"Enter roundabout and take exit onto {road}" if road else "Enter roundabout"
    if mtype in ("turn", "new name", "continue", "merge", "on ramp", "off ramp", "fork", "end of road"):
        if modifier and road:
            return f"{mtype.title()} {modifier} onto {road}"
        if modifier:
            return f"{mtype.title()} {modifier}"
        return f"{mtype.title()} onto {road}" if road else mtype.title()
    # Fallback
    if road:
        return f"{mtype.title()} onto {road}"
    return str(mtype).title()


async def get_walking_route_steps(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    base_url: str = DEFAULT_OSRM_BASE_URL,
    timeout_s: float = 10.0,
) -> tuple[float, float, list[dict[str, Any]]]:
    """Return (distance_m, duration_s, steps) using OSRM walking profile."""
    # OSRM expects lon,lat order
    coords = f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
    url = f"{base_url.rstrip('/')}/route/v1/walking/{coords}"
    params = {"overview": "false", "steps": "true"}
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        r = await client.get(url, params=params, headers={"Accept": "application/json"})
        r.raise_for_status()
        data = r.json()
    routes = data.get("routes") or []
    if not routes:
        return 0.0, 0.0, []
    route0 = routes[0]
    distance_m = float(route0.get("distance") or 0.0)
    duration_s = float(route0.get("duration") or 0.0)
    legs = route0.get("legs") or []
    if not legs:
        return distance_m, duration_s, []
    steps = legs[0].get("steps") or []
    normalized = []
    for s in steps:
        maneuver = s.get("maneuver") or {}
        name = s.get("name")
        normalized.append(
            {
                "instruction": _format_instruction(maneuver, name),
                "distance_m": float(s.get("distance") or 0.0),
                "duration_s": float(s.get("duration") or 0.0),
            }
        )
    return distance_m, duration_s, normalized

