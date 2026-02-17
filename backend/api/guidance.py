"""Guidance endpoints (walking directions from a bus stop)."""

from fastapi import APIRouter, HTTPException

from backend.schemas.guidance import WalkFromStopRequest, WalkGuidanceResponse, WalkStep
from backend.services.osrm import get_walking_route_steps
from backend.services.stops_loader import load_fsu_stops

router = APIRouter(prefix="/guidance", tags=["guidance"])


@router.post("/walk-from-stop", response_model=WalkGuidanceResponse)
async def walk_from_stop(body: WalkFromStopRequest):
    stops = load_fsu_stops()
    stop = next((s for s in stops if str(s.get("id")) == body.stop_id), None)
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")
    origin_lat = float(stop["lat"])
    origin_lng = float(stop["lng"])
    distance_m, duration_s, steps_raw = await get_walking_route_steps(
        origin_lat=origin_lat,
        origin_lng=origin_lng,
        dest_lat=body.dest_lat,
        dest_lng=body.dest_lng,
    )
    steps = [WalkStep(**s) for s in steps_raw]
    return WalkGuidanceResponse(
        origin_stop_id=body.stop_id,
        origin_name=stop.get("name"),
        distance_m=distance_m,
        duration_s=duration_s,
        steps=steps,
    )

