# LastMile-Connect

## Phase 1 – Run locally

1. **Create a virtual env and install dependencies**
   ```bash
   cd LastMile-Connect
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r backend/requirements.txt
   ```

2. **Optional: start Postgres + Redis with Docker**
   ```bash
   docker-compose up -d
   ```
   Copy `.env.example` to `.env` if you want to override defaults.

3. **Run the API** (from project root)
   ```bash
   cd LastMile-Connect
   python run.py
   # or: uvicorn backend.main:app --reload
   ```
   - Root: http://127.0.0.1:8000/
   - Health: http://127.0.0.1:8000/api/health

4. **If you see "database lastmile does not exist"**
   - Ensure Docker Postgres is the one on port 5432: `docker-compose up -d` and stop any local PostgreSQL that uses 5432.
   - Create the DB in the container (if needed):  
     `docker-compose exec postgres psql -U postgres -c "CREATE DATABASE lastmile;"`
   - The app defaults to `postgresql+asyncpg://postgres:postgres@localhost:5433/lastmile` (Docker Postgres on port **5433** to avoid conflict with a local Postgres on 5432). Copy `.env.example` to `.env` and set `DATABASE_URL` if needed.
