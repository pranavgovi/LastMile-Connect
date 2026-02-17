import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import redis.asyncio as aioredis

from backend.api.auth import router as auth_router
from backend.api.health import router as health_router
from backend.api.guidance import router as guidance_router
from backend.api.intents import router as intents_router
from backend.api.sessions import router as sessions_router
from backend.api.stops import router as stops_router
from backend.api.ws import router as ws_router
from backend.config import settings
from backend.database import engine
from backend.models import Base
from backend.redis_client import set_redis
import backend.models.intent  # noqa: F401
import backend.models.rating  # noqa: F401
import backend.models.session  # noqa: F401
import backend.models.user  # noqa: F401
from backend.tasks.auto_end import run_auto_end_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        if getattr(settings, "RESET_DB", False):
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    redis_client = aioredis.from_url(settings.REDIS_URL)
    set_redis(redis_client)
    task = asyncio.create_task(run_auto_end_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await redis_client.close()


app = FastAPI(title="LastMile-Connect", version="0.1.0", lifespan=lifespan)
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(stops_router, prefix="/api")
app.include_router(guidance_router, prefix="/api")
app.include_router(intents_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")
app.include_router(ws_router)

uploads_avatars = Path(__file__).resolve().parent.parent / "uploads" / "avatars"
uploads_avatars.mkdir(parents=True, exist_ok=True)
app.mount("/avatars", StaticFiles(directory=str(uploads_avatars)), name="avatars")


@app.get("/api")
def api_root():
    return {"message": "LastMile-Connect API"}


frontend_path = Path(__file__).resolve().parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    @app.get("/")
    def index():
        return FileResponse(frontend_path / "index.html")

