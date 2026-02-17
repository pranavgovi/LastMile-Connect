"""Session model: anonymous time-bound pair of intents with state machine."""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class SessionState(str, enum.Enum):
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


class Session(Base):
    __tablename__ = "sessions"
    #we need 2 intents and 2 users to create a session.
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    intent_a_id: Mapped[int] = mapped_column(ForeignKey("intents.id", ondelete="CASCADE"), nullable=False, index=True)
    intent_b_id: Mapped[int] = mapped_column(ForeignKey("intents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_a_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_b_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    state: Mapped[SessionState] = mapped_column(
        Enum(SessionState), nullable=False, default=SessionState.REQUESTED, index=True
    )
    token_a: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    token_b: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    sos_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    intent_a = relationship("Intent", foreign_keys=[intent_a_id])
    intent_b = relationship("Intent", foreign_keys=[intent_b_id])
    user_a = relationship("User", foreign_keys=[user_a_id])
    user_b = relationship("User", foreign_keys=[user_b_id])
