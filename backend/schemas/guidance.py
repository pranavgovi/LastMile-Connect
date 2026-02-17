"""Schemas for walking/transit guidance responses."""

from pydantic import BaseModel, Field


class WalkFromStopRequest(BaseModel):
    stop_id: str = Field(..., min_length=1, max_length=128)
    dest_lat: float = Field(..., ge=-90, le=90)
    dest_lng: float = Field(..., ge=-180, le=180)


class WalkStep(BaseModel):
    instruction: str
    distance_m: float
    duration_s: float


class WalkGuidanceResponse(BaseModel):
    origin_stop_id: str
    origin_name: str | None = None
    distance_m: float
    duration_s: float
    steps: list[WalkStep]

