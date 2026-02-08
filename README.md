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

3. **Run the API**
   ```
   or:
   ```bash
   cd LastMile-Connect
   uvicorn backend.main:app --reload
   ```
   - Root: http://127.0.0.1:8000/
   - Health: http://127.0.0.1:8000/api/health
