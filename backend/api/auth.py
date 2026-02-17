"""Auth routes: register, login, profile (GET/PATCH /me), avatar upload."""
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.jwt import create_access_token
from backend.auth.password import hash_password, verify_password
from backend.database import get_db
from backend.deps import get_current_user
from backend.models.user import User
from backend.schemas.user import LoginRequest, Token, UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])

AVATARS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "avatars"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_AVATAR_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/register", response_model=UserResponse)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user. Returns user (no password)."""
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        name=(body.name or "").strip() or None,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email + password; returns JWT access_token."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(data={"sub": str(user.id)}) #
    return Token(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user (requires Bearer token)."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update current user profile (name, has_vehicle)."""
    if body.name is not None:
        current_user.name = (body.name.strip() or None)
    if body.has_vehicle is not None:
        current_user.has_vehicle = body.has_vehicle
    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload profile picture. Accepts image (jpg, png, webp). Max 5MB."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Allowed types: jpg, jpeg, png, webp",
        )
    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File too large (max 5MB)")
    safe_ext = ".jpg" if ext in (".jpeg", ".jpg") else ext
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}{safe_ext}"
    path = AVATARS_DIR / filename
    with open(path, "wb") as f:
        f.write(content)
    if current_user.avatar_url:
        old_path = AVATARS_DIR / Path(current_user.avatar_url).name
        if old_path.exists():
            try:
                os.remove(old_path)
            except OSError:
                pass
    current_user.avatar_url = f"/avatars/{filename}"
    await db.flush()
    await db.refresh(current_user)
    return current_user
