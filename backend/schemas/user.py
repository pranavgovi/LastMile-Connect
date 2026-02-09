"""Pydantic schemas for auth: register, login, user response, token."""
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Request body for POST /auth/register."""
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    """User in API responses (no password)."""
    id: int
    email: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Response for login: access_token and type."""
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Request body for POST /auth/login."""
    email: EmailStr
    password: str
