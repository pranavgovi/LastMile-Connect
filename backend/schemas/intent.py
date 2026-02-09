"""Pydantic schemas for intents: create, response."""
from datetime import datetime

from pydantic import BaseModel, Field


class IntentCreate(BaseModel):
    """Request body for POST /intents."""
    origin_lat: float = Field(..., ge=-90, le=90)
    origin_lng: float = Field(..., ge=-180, le=180)
    dest_lat: float = Field(..., ge=-90, le=90)
    dest_lng: float = Field(..., ge=-180, le=180)
    start_time: datetime | None = None
    end_time: datetime | None = None
    expires_in_minutes: int = Field(default=60, ge=1, le=1440)  # default 1 hour, max 24h


class IntentResponse(BaseModel):
    """Intent in API responses (lat/lng for origin/destination)."""
    id: int
    user_id: int
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float
    start_time: datetime | None
    end_time: datetime | None
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
