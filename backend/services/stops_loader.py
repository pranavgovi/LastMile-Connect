"""Load FSU transit stops from backend/data/fsu_stops.json (populated by fetch_fsu_stops script)."""
from pathlib import Path

_stops_cache: list[dict] | None = None


def _json_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "fsu_stops.json"


def load_fsu_stops() -> list[dict]:
    """Return list of {id, name, lat, lng}. Loads from JSON once and caches."""
    global _stops_cache
    if _stops_cache is not None:
        return _stops_cache
    path = _json_path()
    if not path.exists():
        _stops_cache = []
        return _stops_cache
    import json
    raw = path.read_text(encoding="utf-8")
    _stops_cache = json.loads(raw)
    return _stops_cache


def get_fsu_stop_coords() -> list[tuple[float, float]]:
    """Return list of (lat, lng) for matching (same-stop radius check)."""
    stops = load_fsu_stops()
    return [(s["lat"], s["lng"]) for s in stops]
