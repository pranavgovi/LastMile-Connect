# LastMile-Connect

Safety-first last-mile coordination: short-lived intents, intent matching, anonymous time-bound sessions, live location (WebSocket + Redis), and mock SOS.

## Run locally

1. **Virtual env and dependencies**
   ```bash
   cd LastMile-Connect
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r backend/requirements.txt
   ```

2. **Postgres + Redis (Docker)**
   ```bash
   docker-compose up -d
   ```
   Copy `.env.example` to `.env` to override defaults.

3. **Run the app** (from project root)
   ```bash
   python run.py
   # or: uvicorn backend.main:app --reload
   ```
   - **Frontend:** http://127.0.0.1:8000/
   - **API:** http://127.0.0.1:8000/api
   - **Health:** http://127.0.0.1:8000/api/health

## Flow

1. **Register / Login** → get JWT.
2. **Create intent** → Use my location (GPS) + click map for destination → Create intent.
3. **Find matches** → Select your intent → Find matches → Create session with another intent.
4. **Sessions** → Accept → Activate → (optional) SOS. When ACTIVE, location is streamed via WebSocket and shown on the map.
5. **Complete / Abort** → End session. Auto-end runs for time limit.

## DB / Redis

- **Database:** `postgresql+asyncpg://...@localhost:5433/lastmile` (PostGIS). Create DB if needed: `docker-compose exec postgres psql -U postgres -c "CREATE DATABASE lastmile;"`
- **Redis:** Ephemeral session locations (TTL). Used for live map and optional auto-end.
