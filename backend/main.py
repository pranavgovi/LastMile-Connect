from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.auth import router as auth_router
from backend.api.health import router as health_router
from backend.api.intents import router as intents_router
from backend.database import engine
from backend.models import Base
import backend.models.intent  # noqa: F401 - register Intent with Base.metadata
import backend.models.user  # noqa: F401 - register User with Base.metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup (for dev; use Alembic in production)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="LastMile-Connect", version="0.1.0", lifespan=lifespan)
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(intents_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "LastMile-Connect API"}

