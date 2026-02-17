"""
Import stops from project root stops.txt (GTFS-style CSV) into backend/data/fsu_stops.json.
Filters to FSU bounding box only.

Usage (from project root):
  python -m backend.scripts.import_stops_txt
"""
import csv
import json
from pathlib import Path

# FSU campus + nearby (same as fetch_fsu_stops)
FSU_LAT_MIN = 30.430
FSU_LAT_MAX = 30.458
FSU_LNG_MIN = -84.312
FSU_LNG_MAX = -84.282

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STOPS_TXT = PROJECT_ROOT / "stops.txt"
OUT_JSON = Path(__file__).resolve().parent.parent / "data" / "fsu_stops.json"


def main() -> None:
    if not STOPS_TXT.exists():
        raise SystemExit("stops.txt not found at project root: " + str(STOPS_TXT))
    rows = []
    with open(STOPS_TXT, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                stop_id = (row.get("stop_id") or "").strip()
                stop_name = (row.get("stop_name") or "").strip() or ("Stop " + stop_id)
                lat = float(row.get("stop_lat", 0))
                lng = float(row.get("stop_lon", 0))
            except (ValueError, TypeError):
                continue
            if not (FSU_LAT_MIN <= lat <= FSU_LAT_MAX and FSU_LNG_MIN <= lng <= FSU_LNG_MAX):
                continue
            rows.append({
                "id": stop_id or ("stop-" + str(len(rows))),
                "name": stop_name,
                "lat": round(lat, 6),
                "lng": round(lng, 6),
            })
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("Wrote", len(rows), "stops to", OUT_JSON)


if __name__ == "__main__":
    main()
