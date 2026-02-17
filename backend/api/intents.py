"""Intent routes: create and list (auth required)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from backend.database import get_db
from backend.deps import get_current_user
from backend.models.intent import Intent
from backend.models.session import Session, SessionState
from backend.models.user import User
from backend.schemas.intent import BusStopNearbyResponse, IntentCreate, IntentResponse, MatchCardResponse
from backend.services.matcher import ROUTE_WEIGHT, RATING_WEIGHT, find_matches
from backend.services.stops_loader import get_fsu_stop_coords
from backend.services.ws_updates import updates_manager

router = APIRouter(prefix="/intents", tags=["intents"])


def _point_wkt(lng: float, lat: float) -> str:
    """Build EWKT for a point (PostGIS SRID 4326 = WGS84)."""
    return f"SRID=4326;POINT({lng} {lat})"
#here _point_wkt is a helper function to build the EWKT for a point (PostGIS SRID 4326 = WGS84).
#here EWKT is a Well-Known Text representation of a geometry.
#here SRID is the Spatial Reference System Identifier.
#here WGS84 is the World Geodetic System 1984, a coordinate system for the Earth's surface.
#here POINT is the type of geometry.
#here SRID=4326;POINT({lng} {lat}) is the EWKT for a point.
#here lng is the longitude.
#here lat is the latitude.
#here {lng} {lat} is the coordinates of the point.
#here SRID=4326;POINT({lng} {lat}) is the EWKT for a point.
#here SRID=4326;POINT({lng} {lat}) is the EWKT for a point.

@router.post("", response_model=IntentResponse)
async def create_intent(
    body: IntentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a short-lived intent (origin, destination, time window). One active intent per user."""
    now = datetime.now(timezone.utc)
    existing = await db.execute(
        select(Intent.id).where(Intent.user_id == current_user.id).where(Intent.expires_at > now)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=400,
            detail="You already have an active intent. Complete or let it expire before creating another.",
        )
    expires_at = now + timedelta(minutes=body.expires_in_minutes)
    intent = Intent(
        user_id=current_user.id,
        origin=_point_wkt(body.origin_lng, body.origin_lat),
        destination=_point_wkt(body.dest_lng, body.dest_lat),
        start_time=body.start_time,
        end_time=body.end_time,
        expires_at=expires_at,
    )
    db.add(intent)
    await db.flush()
    await db.refresh(intent)
    await updates_manager.notify_user(current_user.id, {"type": "intents"})
    return IntentResponse(
        id=intent.id,
        user_id=intent.user_id,
        origin_lat=body.origin_lat,
        origin_lng=body.origin_lng,
        dest_lat=body.dest_lat,
        dest_lng=body.dest_lng,
        start_time=intent.start_time,
        end_time=intent.end_time,
        expires_at=intent.expires_at,
        created_at=intent.created_at,
    )


@router.get("", response_model=list[IntentResponse])
async def list_my_intents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List current user's intents (not expired)."""
    now = datetime.now(timezone.utc)
    q = (
        select(
            Intent.id,
            Intent.user_id,
            func.ST_Y(Intent.origin).label("origin_lat"),
            func.ST_X(Intent.origin).label("origin_lng"),
            func.ST_Y(Intent.destination).label("dest_lat"),
            func.ST_X(Intent.destination).label("dest_lng"),
            Intent.start_time,
            Intent.end_time,
            Intent.expires_at,
            Intent.created_at,
        )
        .where(Intent.user_id == current_user.id)
        .where(Intent.expires_at > now)
        .order_by(Intent.created_at.desc())
    )
    result = await db.execute(q)
    rows = result.all()
    return [
        IntentResponse(
            id=r.id,
            user_id=r.user_id,
            origin_lat=float(r.origin_lat),
            origin_lng=float(r.origin_lng),
            dest_lat=float(r.dest_lat),
            dest_lng=float(r.dest_lng),
            start_time=r.start_time,
            end_time=r.end_time,
            expires_at=r.expires_at,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.delete("/{intent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_intent(
    intent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete one of your intents from My intents. Allowed whether or not a session is active. Any session using this intent is also removed (cascade)."""
    result = await db.execute(select(Intent).where(Intent.id == intent_id))
    intent = result.scalar_one_or_none()
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    if intent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your intent")
    # Collect user ids of affected sessions (for WebSocket notify) before cascade delete
    sessions_result = await db.execute(
        select(Session.user_a_id, Session.user_b_id).where(
            (Session.intent_a_id == intent_id) | (Session.intent_b_id == intent_id)
        )
    )
    affected_user_ids = set()
    for row in sessions_result.all():
        affected_user_ids.add(row.user_a_id)
        affected_user_ids.add(row.user_b_id)
    await db.delete(intent)
    await db.flush()
    await updates_manager.notify_user(current_user.id, {"type": "intents"})
    await updates_manager.notify_users(list(affected_user_ids), {"type": "sessions"})
    return None


@router.get("/matches", response_model=list[MatchCardResponse])
async def get_matches(
    intent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return match cards (other intents) ranked by buddy score. Includes route-overlap matches and, if origin is at a bus stop, others at same stop in last 2 min)."""
    result = await db.execute(select(Intent).where(Intent.id == intent_id))
    intent = result.scalar_one_or_none()
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    if intent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your intent")
    # Get origin coords for optional same-stop merge
    origin_result = await db.execute(
        select(
            func.ST_Y(Intent.origin).label("origin_lat"),
            func.ST_X(Intent.origin).label("origin_lng"),
        ).where(Intent.id == intent_id)
    )
    origin_row = origin_result.one_or_none()
    origin_lat = float(origin_row.origin_lat) if origin_row else None
    origin_lng = float(origin_row.origin_lng) if origin_row else None

    matches = await find_matches(db, intent_id)
    cards = []
    seen_intent_ids = set()
    for m in matches:
        rating_part = (m.past_rating_avg or 0) * 20.0
        buddy_score = round(
            ROUTE_WEIGHT * m.route_overlap_score + RATING_WEIGHT * min(100.0, rating_part), 1
        )
        cards.append(
            MatchCardResponse(
                intent_id=m.intent_id,
                user_id=m.user_id,
                name=m.name,
                avatar_url=m.avatar_url,
                has_vehicle=m.has_vehicle,
                origin_lat=m.origin_lat,
                origin_lng=m.origin_lng,
                dest_lat=m.dest_lat,
                dest_lng=m.dest_lng,
                buddy_score=buddy_score,
                route_overlap_score=m.route_overlap_score,
                past_rating_avg=m.past_rating_avg,
                same_bus_stop=False,
            )
        )
        seen_intent_ids.add(m.intent_id)

    # If origin is at a bus stop, add others at same stop (last 2 min) so one "Find matches" is unified
    if origin_lat is not None and origin_lng is not None and _is_near_bus_stop(origin_lat, origin_lng):
        nearby_rows = await _nearby_from_stop(db, current_user.id, origin_lat, origin_lng, within_minutes=2)
        for r in nearby_rows:
            if r.id in seen_intent_ids:
                continue
            seen_intent_ids.add(r.id)
            cards.append(
                MatchCardResponse(
                    intent_id=r.id,
                    user_id=r.user_id,
                    name=r.name,
                    avatar_url=r.avatar_url,
                    has_vehicle=r.has_vehicle,
                    origin_lat=float(r.origin_lat),
                    origin_lng=float(r.origin_lng),
                    dest_lat=float(r.dest_lat),
                    dest_lng=float(r.dest_lng),
                    buddy_score=50.0,
                    route_overlap_score=0.0,
                    past_rating_avg=None,
                    same_bus_stop=True,
                )
            )
    cards.sort(key=lambda c: c.buddy_score, reverse=True)
    return cards


# ~250 m at FSU latitude
BUS_STOP_RADIUS_M = 250
BUS_STOP_RADIUS_DEG = BUS_STOP_RADIUS_M / 111320.0

# FSU bus stops (lat, lng) loaded from backend/data/fsu_stops.json (see scripts/fetch_fsu_stops.py)
def _get_bus_stops() -> list[tuple[float, float]]:
    return get_fsu_stop_coords()


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Approximate distance in km between two WGS84 points."""
    import math
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _is_near_bus_stop(lat: float, lng: float) -> bool:
    stops = _get_bus_stops()
    return any(_haversine_km(lat, lng, s[0], s[1]) <= (BUS_STOP_RADIUS_M / 1000.0) for s in stops)


async def _nearby_from_stop(
    db: AsyncSession,
    current_user_id: int,
    lat: float,
    lng: float,
    within_minutes: int = 2,
):
    """Return rows (id, user_id, origin_lat, origin_lng, dest_lat, dest_lng, name, avatar_url, has_vehicle) for intents at this stop."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(minutes=within_minutes)
    in_session_a = select(Session.intent_a_id).where(Session.state.notin_([SessionState.COMPLETED, SessionState.ABORTED]))
    in_session_b = select(Session.intent_b_id).where(Session.state.notin_([SessionState.COMPLETED, SessionState.ABORTED]))
    stop_point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
    q = (
        select(
            Intent.id,
            Intent.user_id,
            func.ST_Y(Intent.origin).label("origin_lat"),
            func.ST_X(Intent.origin).label("origin_lng"),
            func.ST_Y(Intent.destination).label("dest_lat"),
            func.ST_X(Intent.destination).label("dest_lng"),
            User.name,
            User.avatar_url,
            User.has_vehicle,
        )
        .join(User, Intent.user_id == User.id)
        .where(Intent.user_id != current_user_id)
        .where(Intent.expires_at > now)
        .where(Intent.created_at >= since)
        .where(Intent.id.notin_(in_session_a.union(in_session_b)))
        .where(func.ST_DWithin(Intent.origin, stop_point, BUS_STOP_RADIUS_DEG))
        .order_by(Intent.created_at.desc())
    )
    result = await db.execute(q)
    return result.all()


@router.get("/nearby-from-stop", response_model=list[BusStopNearbyResponse])
async def get_nearby_intents_from_bus_stop(
    lat: float,
    lng: float,
    within_minutes: int = 2,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Intents from other users whose origin is at this bus stop (within ~250m) and created within the last within_minutes. For 'I just got off the bus' matching."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(minutes=within_minutes)
    in_session_a = select(Session.intent_a_id).where(Session.state.notin_([SessionState.COMPLETED, SessionState.ABORTED]))
    in_session_b = select(Session.intent_b_id).where(Session.state.notin_([SessionState.COMPLETED, SessionState.ABORTED]))
    stop_point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
    q = (
        select(
            Intent.id,
            Intent.user_id,
            Intent.created_at,
            func.ST_Y(Intent.origin).label("origin_lat"),
            func.ST_X(Intent.origin).label("origin_lng"),
            func.ST_Y(Intent.destination).label("dest_lat"),
            func.ST_X(Intent.destination).label("dest_lng"),
            User.name,
            User.avatar_url,
            User.has_vehicle,
        )
        .join(User, Intent.user_id == User.id)
        .where(Intent.user_id != current_user.id)
        .where(Intent.expires_at > now)
        .where(Intent.created_at >= since)
        .where(Intent.id.notin_(in_session_a.union(in_session_b)))
        .where(func.ST_DWithin(Intent.origin, stop_point, BUS_STOP_RADIUS_DEG))
        .order_by(Intent.created_at.desc())
    )
    result = await db.execute(q)
    rows = result.all()
    return [
        BusStopNearbyResponse(
            intent_id=r.id,
            user_id=r.user_id,
            name=r.name,
            avatar_url=r.avatar_url,
            has_vehicle=r.has_vehicle,
            origin_lat=float(r.origin_lat),
            origin_lng=float(r.origin_lng),
            dest_lat=float(r.dest_lat),
            dest_lng=float(r.dest_lng),
            created_at=r.created_at,
        )
        for r in rows
    ]
