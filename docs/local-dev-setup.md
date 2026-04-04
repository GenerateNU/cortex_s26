# Local Dev Setup

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Git](https://git-scm.com/)
- A Gemini API key (get one at https://aistudio.google.com/apikey)

## 1. Clone the repo

```bash
git clone git@github.com:GenerateNU/cortex_s26.git
cd cortex_s26
```

## 2. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and fill in the required secrets:

```
LLM_API_KEY=your-gemini-api-key-here
EMBEDDING_API_KEY=your-gemini-api-key-here   # same key works for both
```

If your team uses Supabase for legacy services, also fill in:
```
SUPABASE_URL=http://127.0.0.1:54321          # or your remote Supabase URL
SUPABASE_SERVICE_ROLE_KEY=your-key-here
```

> **Note:** The app's startup sequence calls Supabase. If these are left blank, the backend may crash on boot. Ask your team lead for the correct values.

All other values have working defaults for local dev. Don't commit `.env` — it's gitignored.

## 3. Start everything

```bash
docker compose up
```

This starts two containers:

| Container | What it does | Port |
|-----------|-------------|------|
| `cortex-backend` | FastAPI app with hot reload | `localhost:8000` |
| `cortex-postgres` | PostgreSQL 16 + pgvector | `localhost:5432` |

First run takes a few minutes (building the image + installing Python deps). Subsequent runs are fast due to layer caching.

## 4. Verify it's working

Backend is up:
```bash
curl http://localhost:8000/
# → {"message":"Cortex ETL Backend"}
```

API docs (Swagger UI):
```
http://localhost:8000/docs
```

Connect to Postgres directly:
```bash
psql postgresql://postgres:postgres@localhost:5432/cortex
```

## Common commands

```bash
# Start in background (detached)
docker compose up -d

# View logs
docker compose logs -f backend

# Stop everything (keeps data)
docker compose down

# Stop and delete all data (pgvector + cognee)
docker compose down -v

# Rebuild after changing requirements.txt
docker compose up --build

# Run ruff lint inside the container
docker compose exec backend ruff check

# Run tests inside the container
docker compose exec backend pytest
```

## Troubleshooting

**Port already in use**
```bash
# Find what's using port 8000 or 5432
lsof -i :8000
lsof -i :5432
# Kill it, or change the port mapping in docker-compose.yml
```

**Backend crashes on startup**
- Check logs: `docker compose logs backend`
- Most likely cause: missing env vars in `.env` (especially `LLM_API_KEY`)
- Make sure Docker Desktop is running

**Stale dependencies after pulling new code**
```bash
docker compose up --build
```
This rebuilds the image and reinstalls requirements.

**Want a clean slate?**
```bash
docker compose down -v   # deletes all volumes (database + cognee data)
docker compose up --build
```
