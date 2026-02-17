"""
One-time script to fetch StarMetro (Tallahassee) GTFS and save stops surrounding FSU to backend/data/fsu_stops.json.

Usage:
  # Download from URL (default StarMetro GTFS)
  python -m backend.scripts.fetch_fsu_stops

  # Use a local GTFS zip (e.g. after manual download from Mobility Database)
  python -m backend.scripts.fetch_fsu_stops /path/to/starmetro.zip

  # Custom GTFS URL
  python -m backend.scripts.fetch_fsu_stops --url "https://example.com/gtfs.zip"

Requires: requests (pip install requests)
"""
import argparse
import csv
import json
import re
import sys
import zipfile
from pathlib import Path

# FSU campus + nearby area (Tallahassee): bounding box for filtering stops
FSU_LAT_MIN = 30.430
FSU_LAT_MAX = 30.458
FSU_LNG_MIN = -84.312
FSU_LNG_MAX = -84.282

# Default GTFS URL (StarMetro / TransitFeeds; may redirect)
DEFAULT_GTFS_URL = "https://transitfeeds.com/p/starmetro/885/latest/download"


def slugify(s: str) -> str:
    """Make a short id from stop name (lowercase, alphanumeric + hyphens)."""
    s = re.sub(r"[^\w\s-]", "", s.lower())
    return re.sub(r"[-\s]+", "-", s).strip("-") or "stop"


def fetch_gtfs(url: str, timeout: int = 60) -> bytes:
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "LastMile-Connect/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def parse_stops_from_zip(zip_path: Path) -> list[dict]:
    """Read stops.txt from a GTFS zip; return list of {id, name, lat, lng}."""
    stops = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        if "stops.txt" not in zf.namelist():
            raise SystemExit("stops.txt not found in GTFS zip")
        with zf.open("stops.txt") as f:
            reader = csv.DictReader(f.read().decode("utf-8-sig").splitlines())
            for row in reader:
                try:
                    stop_id = (row.get("stop_id") or "").strip()
                    name = (row.get("stop_name") or "").strip()
                    lat = float(row.get("stop_lat", 0))
                    lng = float(row.get("stop_lon", 0))
                except (ValueError, TypeError):
                    continue
                if not name:
                    continue
                # GTFS allows location_type: 0=stop, 1=station, etc. Skip parent stations if we want only platforms
                location_type = row.get("location_type", "0").strip()
                if location_type and location_type not in ("0", "1"):
                    continue
                stops.append({
                    "id": stop_id or slugify(name)[:50],
                    "name": name,
                    "lat": round(lat, 6),
                    "lng": round(lng, 6),
                })
    return stops


def filter_fsu(stops: list[dict]) -> list[dict]:
    """Keep stops inside FSU bounding box; dedupe by (lat, lng) and assign stable ids."""
    seen = set()
    out = []
    for s in stops:
        lat, lng = s["lat"], s["lng"]
        if not (FSU_LAT_MIN <= lat <= FSU_LAT_MAX and FSU_LNG_MIN <= lng <= FSU_LNG_MAX):
            continue
        key = (round(lat, 5), round(lng, 5))
        if key in seen:
            continue
        seen.add(key)
        # Prefer a readable id: slug of name plus first part of original id if needed for uniqueness
        rid = s.get("id", "") or slugify(s["name"])
        if not rid.replace("-", "").replace("_", "").isalnum():
            rid = slugify(s["name"])
        out.append({
            "id": rid[:64],
            "name": s["name"],
            "lat": s["lat"],
            "lng": s["lng"],
        })
    return sorted(out, key=lambda x: (-x["lat"], x["lng"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch GTFS and save FSU stops to JSON")
    parser.add_argument("path_or_url", nargs="?", help="Path to local .zip or leave empty to download")
    parser.add_argument("--url", help="GTFS zip URL (overrides default)")
    parser.add_argument("--out", help="Output JSON path (default: backend/data/fsu_stops.json)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent.parent
    out_path = Path(args.out) if args.out else root / "backend" / "data" / "fsu_stops.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    zip_path: Path | None = None
    if args.path_or_url:
        p = Path(args.path_or_url)
        if p.suffix.lower() == ".zip" and p.exists():
            zip_path = p
        elif p.suffix.lower() == ".zip" or args.path_or_url.startswith("http"):
            # URL
            url = args.path_or_url
            if args.url:
                url = args.url
            print("Downloading GTFS from", url, "...")
            try:
                data = fetch_gtfs(url)
            except Exception as e:
                print("Download failed:", e, file=sys.stderr)
                sys.exit(1)
            zip_path = out_path.parent / "gtfs_temp.zip"
            zip_path.write_bytes(data)
            print("Downloaded.", flush=True)
    if args.url and not zip_path:
        print("Downloading GTFS from", args.url, "...")
        try:
            data = fetch_gtfs(args.url)
        except Exception as e:
            print("Download failed:", e, file=sys.stderr)
            sys.exit(1)
        zip_path = out_path.parent / "gtfs_temp.zip"
        zip_path.write_bytes(data)
        print("Downloaded.", flush=True)
    if not zip_path:
        # Default: try to download
        url = DEFAULT_GTFS_URL
        print("Downloading StarMetro GTFS from", url, "...")
        try:
            data = fetch_gtfs(url)
        except Exception as e:
            print("Download failed:", e, file=sys.stderr)
            print("To use a local file: python -m backend.scripts.fetch_fsu_stops /path/to/starmetro.zip", file=sys.stderr)
            sys.exit(1)
        zip_path = out_path.parent / "gtfs_temp.zip"
        zip_path.write_bytes(data)
        print("Downloaded.", flush=True)

    try:
        stops = parse_stops_from_zip(zip_path)
        print("Parsed", len(stops), "stops from GTFS.")
        fsu = filter_fsu(stops)
        print("Filtered to", len(fsu), "stops in FSU area.")
    finally:
        if zip_path and zip_path.name == "gtfs_temp.zip":
            zip_path.unlink(missing_ok=True)

    out_path.write_text(json.dumps(fsu, indent=2), encoding="utf-8")
    print("Wrote", out_path)


if __name__ == "__main__":
    main()
