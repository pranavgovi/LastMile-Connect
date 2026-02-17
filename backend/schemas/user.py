"""Pydantic schemas for auth: register, login, user response, token."""
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Request body for POST /auth/register."""
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str | None = Field(default=None, max_length=255)


class UserResponse(BaseModel):
    """User in API responses (no password)."""
    id: int
    email: str
    name: str | None = None
    avatar_url: str | None = None
    has_vehicle: bool = False

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Request body for PATCH /auth/me (profile update)."""
    name: str | None = Field(default=None, max_length=255)
    has_vehicle: bool | None = None


class Token(BaseModel):
    """Response for login: access_token and type."""
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Request body for POST /auth/login."""
    email: EmailStr
    password: str
