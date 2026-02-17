"""Session routes: create, list mine, accept, activate, complete, abort."""
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from backend.database import get_db
from backend.deps import get_current_user
from backend.models.intent import Intent
from backend.models.session import Session, SessionState
from backend.models.user import User
from backend.redis_client import get_redis
from backend.schemas.session import RoutePoint, RoutePoints, SessionCreate, SessionResponse
from backend.services.location_store import get_locations
from backend.services.state_machine import transition
from backend.services.ws_updates import updates_manager

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _session_to_response(
    session: Session,
    current_user_id: int,
    route_a: RoutePoints | None = None,
    route_b: RoutePoints | None = None,
) -> SessionResponse:
    my_side = None
    my_token = None
    if session.user_a_id == current_user_id:
        my_side = "a"
        my_token = session.token_a
    elif session.user_b_id == current_user_id:
        my_side = "b"
        my_token = session.token_b
    return SessionResponse(
        id=session.id,
        intent_a_id=session.intent_a_id,
        intent_b_id=session.intent_b_id,
        user_a_id=session.user_a_id,
        user_b_id=session.user_b_id,
        state=session.state,
        started_at=session.started_at,
        ends_at=session.ends_at,
        max_duration_minutes=session.max_duration_minutes,
        created_at=session.created_at,
        my_side=my_side,
        my_token=my_token,
        sos_at=getattr(session, "sos_at", None),
        route_a=route_a,
        route_b=route_b,
    )


@router.post("", response_model=SessionResponse)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a session linking two intents (both must exist). One active session per user per side."""
    r_a = await db.execute(select(Intent).where(Intent.id == body.intent_a_id))
    r_b = await db.execute(select(Intent).where(Intent.id == body.intent_b_id))
    intent_a = r_a.scalar_one_or_none()
    intent_b = r_b.scalar_one_or_none()
    if not intent_a or not intent_b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intent not found")
    if intent_a.id == intent_b.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use two different intents")
    if current_user.id != intent_a.user_id and current_user.id != intent_b.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You must own one of the intents")
    non_terminal = [SessionState.REQUESTED, SessionState.ACCEPTED, SessionState.ACTIVE]
    my_active = await db.execute(
        select(Session.id).where(
            (Session.user_a_id == current_user.id) | (Session.user_b_id == current_user.id)
        ).where(Session.state.in_(non_terminal))
    )
    if my_active.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active session. Complete or abort it first.",
        )
    other_user_id = intent_b.user_id if current_user.id == intent_a.user_id else intent_a.user_id
    other_active = await db.execute(
        select(Session.id).where(
            (Session.user_a_id == other_user_id) | (Session.user_b_id == other_user_id)
        ).where(Session.state.in_(non_terminal))
    )
    if other_active.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That user already has an active session. Try another match.",
        )
    # Ensure consistent order: current user is user_a if they own intent_a
    if current_user.id == intent_b.user_id:
        intent_a, intent_b = intent_b, intent_a
    token_a = secrets.token_urlsafe(32)
    token_b = secrets.token_urlsafe(32)
    session = Session(
        intent_a_id=intent_a.id,
        intent_b_id=intent_b.id,
        user_a_id=intent_a.user_id,
        user_b_id=intent_b.user_id,
        state=SessionState.REQUESTED,
        token_a=token_a,
        token_b=token_b,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    q_route = (
        select(
            Intent.id,
            func.ST_Y(Intent.origin).label("oy"),
            func.ST_X(Intent.origin).label("ox"),
            func.ST_Y(Intent.destination).label("dy"),
            func.ST_X(Intent.destination).label("dx"),
        ).where(Intent.id.in_([intent_a.id, intent_b.id]))
    )
    r_route = await db.execute(q_route)
    route_by_id = {}
    for row in r_route.all():
        route_by_id[row.id] = RoutePoints(
            origin=RoutePoint(lat=float(row.oy), lng=float(row.ox)),
            destination=RoutePoint(lat=float(row.dy), lng=float(row.dx)),
        )
    await updates_manager.notify_users([intent_a.user_id, intent_b.user_id], {"type": "sessions"})
    return _session_to_response(
        session,
        current_user.id,
        route_a=route_by_id.get(intent_a.id),
        route_b=route_by_id.get(intent_b.id),
    )


@router.get("/me", response_model=list[SessionResponse])
async def list_my_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List sessions where the current user is party A or B (non-terminal states only by default)."""
    q = select(Session).where(
        (Session.user_a_id == current_user.id) | (Session.user_b_id == current_user.id)
    ).where(Session.state.notin_([SessionState.COMPLETED, SessionState.ABORTED])).order_by(Session.created_at.desc())
    result = await db.execute(q)
    sessions = result.scalars().all()
    if not sessions:
        return []
    intent_ids = set()
    for s in sessions:
        intent_ids.add(s.intent_a_id)
        intent_ids.add(s.intent_b_id)
    route_by_intent = {}
    q_intents = (
        select(
            Intent.id,
            func.ST_Y(Intent.origin).label("origin_lat"),
            func.ST_X(Intent.origin).label("origin_lng"),
            func.ST_Y(Intent.destination).label("dest_lat"),
            func.ST_X(Intent.destination).label("dest_lng"),
        ).where(Intent.id.in_(intent_ids))
    )
    r_intents = await db.execute(q_intents)
    for row in r_intents.all():
        route_by_intent[row.id] = RoutePoints(
            origin=RoutePoint(lat=float(row.origin_lat), lng=float(row.origin_lng)),
            destination=RoutePoint(lat=float(row.dest_lat), lng=float(row.dest_lng)),
        )
    return [
        _session_to_response(
            s,
            current_user.id,
            route_a=route_by_intent.get(s.intent_a_id),
            route_b=route_by_intent.get(s.intent_b_id),
        )
        for s in sessions
    ]


def _get_my_token(session: Session, user_id: int) -> str:
    if session.user_a_id == user_id:
        return session.token_a
    if session.user_b_id == user_id:
        return session.token_b
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a party to this session")


async def _do_transition(
    session_id: int,
    to_state: SessionState,
    db: AsyncSession,
    current_user: User,
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    token = _get_my_token(session, current_user.id)
    try:
        session = await transition(db, session_id, to_state, token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    await updates_manager.notify_users([session.user_a_id, session.user_b_id], {"type": "sessions"})
    return _session_to_response(session, current_user.id)


@router.post("/{session_id}/accept", response_model=SessionResponse)
async def accept_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move session from REQUESTED to ACCEPTED."""
    return await _do_transition(session_id, SessionState.ACCEPTED, db, current_user)


@router.post("/{session_id}/activate", response_model=SessionResponse)
async def activate_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move session from ACCEPTED to ACTIVE (sets started_at)."""
    return await _do_transition(session_id, SessionState.ACTIVE, db, current_user)


@router.post("/{session_id}/complete", response_model=SessionResponse)
async def complete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move session from ACTIVE to COMPLETED."""
    return await _do_transition(session_id, SessionState.COMPLETED, db, current_user)


@router.post("/{session_id}/abort", response_model=SessionResponse)
async def abort_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move session to ABORTED (from REQUESTED, ACCEPTED, or ACTIVE)."""
    return await _do_transition(session_id, SessionState.ABORTED, db, current_user)


@router.post("/{session_id}/sos", response_model=SessionResponse)
async def session_sos(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark session as SOS requested (mock; for demo)."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    _get_my_token(session, current_user.id)
    session.sos_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(session)
    await updates_manager.notify_users([session.user_a_id, session.user_b_id], {"type": "sessions"})
    return _session_to_response(session, current_user.id)


@router.get("/{session_id}/locations")
async def session_locations(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current live locations for both parties (ACTIVE session only; from Redis)."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    _get_my_token(session, current_user.id)
    if session.state != SessionState.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session not active")
    redis = await get_redis()
    return await get_locations(redis, session_id)
