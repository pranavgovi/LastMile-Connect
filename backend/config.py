from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database (port 5433 matches docker-compose postgres mapping; use 5432 for local Postgres)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/lastmile"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Session / location TTL (seconds)
    SESSION_LOCATION_TTL_SECONDS: int = 300

    # Set to true to drop all tables and recreate on startup (fixes schema e.g. has_vehicle). All data is lost.
    RESET_DB: bool = False
    # OAuth (optional)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
