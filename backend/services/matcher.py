"""Find intents that are nearby and time-overlapping (for session creation). Returns match cards with buddy score."""
import math
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from backend.models.intent import Intent
from backend.models.rating import Rating
from backend.models.session import Session, SessionState
from backend.models.user import User


# Meters; origin within this distance considered "nearby"
ORIGIN_RADIUS_M = 2000
GEOGRAPHY_RADIUS_M = ORIGIN_RADIUS_M

# Buddy score: weight for route overlap vs past rating (0-1 each)
ROUTE_WEIGHT = 0.7
RATING_WEIGHT = 0.3


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Approximate distance in km between two WGS84 points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@dataclass
class MatchResult:
    intent_id: int
    user_id: int
    name: str | None
    avatar_url: str | None
    has_vehicle: bool
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float
    route_overlap_score: float
    past_rating_avg: float | None


async def find_matches(
    db: AsyncSession,
    intent_id: int,
    limit: int = 20,
) -> list[MatchResult]:
    """
    Return match cards: other intents that are nearby, time-overlapping, and satisfy vehicle rule.
    Vehicle rule: if my intent's user has_vehicle, match must be from a user without vehicle (walker).
    Exclude intents already in a non-terminal session.
    Scores: route_overlap_score 0-100, past_rating_avg 0-5 (or None).
    """
    now = datetime.now(timezone.utc)
    in_session = select(Session.intent_a_id).where(Session.state.notin_([SessionState.COMPLETED, SessionState.ABORTED]))
    in_session_b = select(Session.intent_b_id).where(Session.state.notin_([SessionState.COMPLETED, SessionState.ABORTED]))

    # Load source intent with coords and source user (for has_vehicle and route scoring)
    q_source = select(
        Intent.id,
        Intent.user_id,
        func.ST_Y(Intent.origin).label("origin_lat"),
        func.ST_X(Intent.origin).label("origin_lng"),
        func.ST_Y(Intent.destination).label("dest_lat"),
        func.ST_X(Intent.destination).label("dest_lng"),
        Intent.start_time,
        Intent.end_time,
    ).where(Intent.id == intent_id)
    src_row = (await db.execute(q_source)).one_or_none()
    if not src_row:
        return []

    src_user = (await db.execute(select(User).where(User.id == src_row.user_id))).scalar_one_or_none()
    if not src_user:
        return []
    source_origin_lat = float(src_row.origin_lat)
    source_origin_lng = float(src_row.origin_lng)
    source_dest_lat = float(src_row.dest_lat)
    source_dest_lng = float(src_row.dest_lng)

    source_origin_subq = select(Intent.origin).where(Intent.id == intent_id).scalar_subquery()

    # Match intents: join User to filter by has_vehicle and get name/avatar for trust
    q = (
        select(
            Intent.id,
            Intent.user_id,
            User.name,
            User.avatar_url,
            User.has_vehicle,
            func.ST_Y(Intent.origin).label("origin_lat"),
            func.ST_X(Intent.origin).label("origin_lng"),
            func.ST_Y(Intent.destination).label("dest_lat"),
            func.ST_X(Intent.destination).label("dest_lng"),
        )
        .join(User, Intent.user_id == User.id)
        .where(Intent.id != intent_id)
        .where(Intent.user_id != src_row.user_id)
        .where(Intent.expires_at > now)
        .where(Intent.id.notin_(in_session.union(in_session_b)))
        .where(
            func.ST_DWithin(
                Intent.origin,
                source_origin_subq,
                GEOGRAPHY_RADIUS_M / 111320.0,
            )
        )
    )
    if src_user.has_vehicle:
        q = q.where(User.has_vehicle.is_(False))
    if src_row.start_time is not None and src_row.end_time is not None:
        q = q.where(
            or_(
                Intent.start_time.is_(None),
                Intent.end_time.is_(None),
                and_(
                    Intent.start_time <= src_row.end_time,
                    Intent.end_time >= src_row.start_time,
                ),
            )
        )
    q = q.order_by(Intent.created_at.desc()).limit(limit)
    rows = (await db.execute(q)).all()

    # Past ratings for match users
    match_user_ids = [r.user_id for r in rows]
    q_ratings = (
        select(Rating.ratee_id, func.avg(Rating.score).label("avg_score"))
        .where(Rating.ratee_id.in_(match_user_ids))
        .group_by(Rating.ratee_id)
    )
    rating_map = {r.ratee_id: float(r.avg_score) for r in (await db.execute(q_ratings)).all()}

    results = []
    for r in rows:
        o_lat, o_lng = float(r.origin_lat), float(r.origin_lng)
        d_lat, d_lng = float(r.dest_lat), float(r.dest_lng)
        d_origin_km = _haversine_km(source_origin_lat, source_origin_lng, o_lat, o_lng)
        d_dest_km = _haversine_km(source_dest_lat, source_dest_lng, d_lat, d_lng)
        total_km = d_origin_km + d_dest_km
        route_overlap_score = 100.0 * math.exp(-total_km / 5.0)
        past_rating_avg = rating_map.get(r.user_id)
        results.append(
            MatchResult(
                intent_id=r.id,
                user_id=r.user_id,
                name=getattr(r, "name", None),
                avatar_url=getattr(r, "avatar_url", None),
                has_vehicle=r.has_vehicle,
                origin_lat=o_lat,
                origin_lng=o_lng,
                dest_lat=d_lat,
                dest_lng=d_lng,
                route_overlap_score=round(route_overlap_score, 1),
                past_rating_avg=round(past_rating_avg, 1) if past_rating_avg is not None else None,
            )
        )

    return results
