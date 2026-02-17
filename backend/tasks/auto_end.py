"""Auto-end ACTIVE sessions by time limit."""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import async_session
from backend.models.session import Session, SessionState

CHECK_INTERVAL_SECONDS = 60


async def run_auto_end_once() -> None:
    now = datetime.now(timezone.utc)
    async with async_session() as db:
        result = await db.execute(
            select(Session).where(Session.state == SessionState.ACTIVE)
        )
        sessions = result.scalars().all()
        for session in sessions:
            if session.started_at:
                ends = session.started_at + timedelta(minutes=session.max_duration_minutes)
                if now >= ends:
                    await db.execute(update(Session).where(Session.id == session.id).values(state=SessionState.COMPLETED))
        await db.commit()


async def run_auto_end_loop() -> None:
    while True:
        try:
            await run_auto_end_once()
        except Exception:
            pass
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
