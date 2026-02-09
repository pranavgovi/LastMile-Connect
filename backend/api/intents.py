"""Intent routes: create and list (auth required)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from backend.database import get_db
from backend.deps import get_current_user
from backend.models.intent import Intent
from backend.models.user import User
from backend.schemas.intent import IntentCreate, IntentResponse

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
    """Create a short-lived intent (origin, destination, time window)."""
    now = datetime.now(timezone.utc)
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
            #ST_Y, ST_X are used to get the latitude and longitude of the origin and destination points from the POSTGIS database and return
            # to the users as meaningful column names.            func.ST_Y(Intent.origin).label("origin_lat"), 
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
