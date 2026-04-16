# Cortex

Document knowledge graph system powered by [Cognee](https://github.com/topoteretes/cognee). Ingests PDFs, CSVs, and text files, builds a knowledge graph via LLM-driven extraction, and serves semantic search over the resulting graph.

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.12, Uvicorn |
| Knowledge graph | Cognee SDK (Kuzu graph store, pgvector, Gemini LLM) |
| Database | PostgreSQL 16 + pgvector |
| Document metadata | Supabase (async client) |
| Object storage | Cloudflare R2 (optional) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Data fetching | TanStack Query v5, Axios |
| Graph visualization | react-force-graph-2d |

## Prerequisites

- Python 3.12
- Node.js 18+
- Docker and Docker Compose (for containerized setup)
- A Google Gemini API key (used for LLM and embeddings)

## Getting started

### 1. Clone and configure environment

```bash
git clone <repo-url>
cd cortex_s26
cp .env.example .env
```

Open `.env` and fill in the required secrets:

```
LLM_API_KEY=<your-gemini-api-key>
EMBEDDING_API_KEY=<your-gemini-api-key>
SUPABASE_URL=<your-supabase-url>
SUPABASE_SERVICE_ROLE_KEY=<your-supabase-key>
```

The rest of the defaults work for local development. See `.env.example` for the full list.

### 2a. Docker setup (recommended)

```bash
docker compose up
```

This starts:

- **backend** at `http://localhost:8000` (FastAPI with hot-reload)
- **postgres** at `localhost:5433` (pgvector/pgvector:pg16)

The backend container mounts `./backend` as a volume, so code changes reload automatically.

### 2b. Manual setup

**Backend:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

This requires a running PostgreSQL instance with the pgvector extension. Update `DB_*` and `VECTOR_DB_URL` in `.env` to match your database.

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

The dev server starts at `http://localhost:3000`.

> **Note:** Set `CORS_ALLOWED_ORIGINS=http://localhost:3000` in `.env` so the backend accepts requests from the frontend.

## Project structure

```
cortex_s26/
├── backend/
│   ├── app/
│   │   ├── main.py                        # FastAPI app, lifespan startup
│   │   ├── api.py                         # Central router, mounts all sub-routers under /api
│   │   ├── cognee_config.py               # Cognee SDK initialization
│   │   ├── routes/
│   │   │   └── documents.py               # Upload, search, graph, list, file-url
│   │   ├── services/
│   │   │   ├── document_pipeline.py       # Background ingest orchestration
│   │   │   ├── document_metadata_service.py  # Supabase CRUD for documents
│   │   │   ├── cognee_service.py          # Knowledge graph search
│   │   │   ├── graph_service.py           # D3-compatible graph data
│   │   │   └── storage.py                 # Cloudflare R2 operations
│   │   ├── core/                          # Supabase client, LiteLLM client, webhooks
│   │   └── utils/                         # Validation helpers
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/                         # SearchPage, UploadPage, DocumentsPage,
│       │                                  # DocumentDetailPage, GraphPage
│       ├── components/                    # Navbar, NodeDetailPanel
│       └── services/api.ts               # Axios client and TypeScript types
├── supabase/migrations/                   # Schema migrations
├── .github/workflows/                     # CI/CD pipelines
├── docker-compose.yml
└── .env.example
```

## API endpoints

All routes are mounted under `/api` via `app/api.py`.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/documents/upload` | Upload up to 5 files (.pdf, .csv, .txt) |
| `GET` | `/api/documents/search?q=...` | Search the knowledge graph |
| `GET` | `/api/documents/graph` | D3-compatible node/link JSON |
| `GET` | `/api/documents/` | List all documents |
| `GET` | `/api/documents/{id}` | Single document by ID |
| `GET` | `/api/documents/{id}/file-url` | Pre-signed R2 download URL |
| `GET` | `/api/health` | Health check |

## Running tests

```bash
cd backend
pytest                              # all tests
pytest tests/test_integration.py    # integration tests only
pytest -v                           # verbose output
```

`test_storage.py` and `test_cognee.py` require live credentials and are skipped in CI.

## Linting and formatting

**Backend (Ruff):**

```bash
cd backend
ruff check            # lint (must pass before merge)
ruff check --fix      # auto-fix lint issues
ruff format           # auto-format
```

**Frontend (ESLint + Prettier):**

```bash
cd frontend
npx eslint src/
npx prettier --check src/
npx prettier --write src/    # auto-format
```

## CI/CD

GitHub Actions run on every PR:

| Workflow | What it checks |
|----------|---------------|
| `backend-lint-check.yml` | Ruff lint |
| `backend-test.yml` | pytest (skips credential-dependent tests) |
| `frontend-lint-check.yml` | ESLint |
| `frontend-prettier-check.yml` | Prettier formatting |
| `docker-build.yml` | Docker image builds |

## Branch and PR conventions

**Branches:** `<issue-number>-<short-kebab-description>`

Use GitHub's "Create a branch" button on the issue. Example: `35-build-knowledge-search-service`

**PR titles:** use a conventional commit prefix with an imperative description.

| Prefix | Use for | Example |
|--------|---------|---------|
| `feat:` | New functionality | `feat: build knowledge search service (#35)` |
| `fix:` | Bug fix | `fix: delete temp files in finally block` |
| `chore:` | Deps, config, tooling | `chore: add cognee dependencies` |
| `docs:` | Documentation | `docs: cognee pipeline notes` |
| `test:` | Tests only | `test: add integration test suite` |

**PR body:** must include `Closes #<number>` to link the related issue.

## Environment variables

See `.env.example` for a copy-paste template. Key variables:

| Variable | Required | Notes |
|----------|----------|-------|
| `LLM_API_KEY` | Yes | Gemini API key |
| `LLM_PROVIDER` / `LLM_MODEL` | Yes | Defaults: `gemini` / `gemini/gemini-flash-latest` |
| `EMBEDDING_API_KEY` | Yes | Can reuse `LLM_API_KEY` for Gemini |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role key |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Yes | PostgreSQL connection (overridden by Docker Compose) |
| `VECTOR_DB_URL` | Yes | pgvector connection string |
| `CLOUDFLARE_R2_*` | No | Omit to skip file storage |
| `COGNEE_TIMEOUT_SECONDS` | No | Default: 300s |
