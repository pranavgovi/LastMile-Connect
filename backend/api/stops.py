"""Stored FSU transit stops (from one-time GTFS fetch). Public, no auth."""
from fastapi import APIRouter

from backend.services.stops_loader import load_fsu_stops

router = APIRouter(prefix="/stops", tags=["stops"])


@router.get("")
def list_stops():
    """Return transit stops surrounding FSU (from backend/data/fsu_stops.json)."""
    return load_fsu_stops()
