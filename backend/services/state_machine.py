"""Session state machine: enforce allowed transitions and side (token)."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.session import Session, SessionState

# Allowed transitions: from_state -> {to_state, ...}
ALLOWED: dict[SessionState, set[SessionState]] = {
    SessionState.REQUESTED: {SessionState.ACCEPTED, SessionState.ABORTED},
    SessionState.ACCEPTED: {SessionState.ACTIVE, SessionState.ABORTED},
    SessionState.ACTIVE: {SessionState.COMPLETED, SessionState.ABORTED},
    SessionState.COMPLETED: set(),
    SessionState.ABORTED: set(),
}


async def transition(
    db: AsyncSession,
    session_id: int,
    to_state: SessionState,
    token: str,
) -> Session:
    """
    Transition session to to_state if token is valid for this session and transition is allowed.
    Sets started_at when moving to ACTIVE. Returns updated Session; raises ValueError if invalid.
    """
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError("Session not found")
    if token not in (session.token_a, session.token_b):
        raise ValueError("Invalid token for this session")
    current = session.state
    if current in (SessionState.COMPLETED, SessionState.ABORTED):
        raise ValueError("Session already ended")
    if to_state not in ALLOWED.get(current, set()):
        raise ValueError(f"Transition {current.value} -> {to_state.value} not allowed")
    session.state = to_state
    if to_state == SessionState.ACTIVE and session.started_at is None:
        session.started_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(session)
    return session
