"""Pydantic schemas for sessions."""
from datetime import datetime

from pydantic import BaseModel

from backend.models.session import SessionState


class RoutePoint(BaseModel):
    lat: float
    lng: float


class RoutePoints(BaseModel):
    origin: RoutePoint
    destination: RoutePoint


class SessionCreate(BaseModel):
    """Request to create a session (link two intents). For matcher or manual testing."""
    intent_a_id: int
    intent_b_id: int


class SessionResponse(BaseModel):
    """Session in API responses. Include your token only for the side you belong to."""
    id: int
    intent_a_id: int
    intent_b_id: int
    user_a_id: int
    user_b_id: int
    state: SessionState
    started_at: datetime | None
    ends_at: datetime | None
    max_duration_minutes: int
    sos_at: datetime | None = None
    created_at: datetime
    my_side: str | None = None
    my_token: str | None = None
    route_a: RoutePoints | None = None
    route_b: RoutePoints | None = None

    class Config:
        from_attributes = True
