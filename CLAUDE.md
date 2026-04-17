# Cortex

Document knowledge graph system powered by Cognee. Ingests PDFs/CSVs/text via `cognee.add()` → `cognee.cognify()`, then serves knowledge-graph search via `SearchType.GRAPH_COMPLETION`.

## What to ignore
- `archive/` — deprecated, do not review
- `backend/app/services/extraction/` — old ETL pipeline, being replaced
- `supabase/` — not part of current sprint

## Active codebase (review here)
- `backend/app/` — all active backend code
- `backend/tests/` — pytest tests
- `frontend/` — React SPA (active development)

## Tech stack

### Backend
- FastAPI + Uvicorn (Python 3.12)
- Cognee (`cognee[postgres,gemini]>=0.5.5`) — knowledge graph engine
  - Graph store: Kuzu (embedded, `.cognee_system/`)
  - Vector store: pgvector via PostgreSQL
  - LLM: Google Gemini (`LLM_PROVIDER=gemini`)
  - Embeddings: configured via `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL`
- Supabase — document metadata, async client
- LiteLLM — LLM abstraction layer
- Cloudflare R2 — raw file storage (pre-signed URLs via `boto3`)
- Ruff for linting/formatting

### Frontend
- React 18 + TypeScript
- Vite (dev server + build)
- Tailwind CSS
- React Router v6
- React Query (TanStack Query v5)
- react-force-graph-2d — knowledge graph visualization
- Axios — HTTP client

## Architecture

All routes are mounted under `/api` via `app/api.py`.

```
POST /api/documents/upload
  → save file to /tmp/cognee_uploads/
  → create_document() in Supabase (status=processing)
  → run_pipeline() in background:
      → upload_to_r2() (raw file to Cloudflare R2)
      → LLM-based client name + document type classification
      → cognee.add(file_path, dataset_name=client_name)
      → cognee.cognify(datasets=[client_name])
      → cognee.search(SearchType.CHUNKS) × 3 for summary/insights/entities
      → write results to Supabase (status=completed)

GET /api/documents/search?q=...&dataset=...&search_type=...
  → search_knowledge_graph(query, dataset, limit, search_type)
      → cognee.search(SearchType.GRAPH_COMPLETION, ...)

GET /api/documents/graph
  → get_graph_data() → D3-compatible node/link JSON

GET /api/documents/          — list all documents
GET /api/documents/{doc_id}  — single document
GET /api/documents/{doc_id}/file-url — pre-signed R2 download URL
GET /api/health              — Supabase connectivity check
```

### Key files
- `app/main.py` — FastAPI app, lifespan (Supabase → wait_for_supabase → webhooks → queue → Cognee → recover_stale_documents)
- `app/api.py` — central router, mounts all sub-routers under `/api`
- `app/cognee_config.py` — `setup_cognee()`, wired into lifespan
- `app/routes/documents.py` — upload, search, graph, list, get, file-url
- `app/services/ingest.py` — `check_cognee_storage()` (startup writability check for `.cognee_system/`)
- `app/services/cognee_service.py` — `search_knowledge_graph()` (used by `/documents/search` route)
- `app/services/document_pipeline.py` — `run_pipeline()` (background ingest orchestration)
- `app/services/document_metadata_service.py` — Supabase CRUD for document records + `recover_stale_documents()`
- `app/services/graph_service.py` — `get_graph_data()` for D3 visualization
- `app/services/storage.py` — `upload_to_r2()` and `get_presigned_url()` for Cloudflare R2
- `app/services/supabase_check.py` — `wait_for_supabase()` (startup health check)
- `app/utils/validation.py` — `sanitize_dataset_name()`, `validate_dataset_name()`
- `app/core/` — Supabase client, LiteLLM client, webhooks, dependencies

### Frontend pages
- `/` → `SearchPage` — knowledge graph search
- `/upload` → `UploadPage` — document upload
- `/documents` → `DocumentsPage` — document list
- `/documents/:id` → `DocumentDetailPage` — single document view
- `/graph` → `GraphPage` — force-graph visualization

## Running the project
```bash
# Postgres (pgvector) — required for Cognee; exposes localhost:5433
docker compose up -d postgres

# Local Supabase stack — metadata store (PostgREST on :54321, Postgres on :54322)
# Applies supabase/migrations/*.sql automatically. Run once per machine, persists across restarts.
supabase start
# If cortex_documents schema is out of date after pulling new migrations:
supabase db reset --local

# Backend
cd backend
python -m uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev
```

Point `.env` at the local Supabase:
- `SUPABASE_URL=http://127.0.0.1:54321`
- `SUPABASE_SERVICE_ROLE_KEY=<value from "supabase status -o env">`

## Running tests
```bash
cd backend && pytest
```

## Linting (enforced in CI on every PR)
```bash
cd backend && ruff check   # must pass before merge
cd backend && ruff format  # auto-format
```

## CI/CD (GitHub Actions)
- `backend-lint-check.yml` — Ruff lint on backend PRs
- `backend-test.yml` — pytest on backend PRs (skips `test_storage.py` and `test_cognee.py` which need credentials)
- `frontend-lint-check.yml` — ESLint on frontend PRs
- `frontend-prettier-check.yml` — Prettier format check on frontend PRs
- `docker-build.yml` — Docker image build
- `claude.yml` / `claude-code-review.yml` — Claude Code automation
- `cleanup-ghcr.yml` — GHCR image cleanup
- `supabase-deploy.yml` — Supabase deployment

## Required environment variables

See `.env.example` (project root) for a copy-paste template.

```
# General
ENVIRONMENT, CORS_ALLOWED_ORIGINS

# Supabase (required — used by lifespan, document metadata, search)
SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

# LLM / Embeddings
LLM_PROVIDER, LLM_MODEL, LLM_API_KEY
EMBEDDING_PROVIDER, EMBEDDING_MODEL, EMBEDDING_API_KEY

# Cognee persistence (read by Cognee SDK internally, not by app code)
VECTOR_DB_PROVIDER, VECTOR_DB_URL
DB_PROVIDER, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# Cognee timeout (optional, default 300s)
COGNEE_TIMEOUT_SECONDS

# Cognee storage path (optional, default ".cognee_system")
COGNEE_SYSTEM_PATH

# Webhooks (required if webhook dispatch is enabled in lifespan)
WEBHOOK_BASE_URL, WEBHOOK_SECRET

# Object storage (optional — Cloudflare R2)
CLOUDFLARE_R2_ENDPOINT, CLOUDFLARE_R2_ACCESS_KEY_ID, CLOUDFLARE_R2_SECRET_KEY, CLOUDFLARE_R2_BUCKET_NAME
```

## Branch & PR naming

**Branches:** `<issue-number>-<short-kebab-description>`
> Use GitHub's "Create a branch" button on the issue — it generates this automatically.
> Example: `35-build-knowledge-search-service`

**PR titles:** conventional commits prefix + imperative description
- `feat:` new functionality — `feat: build knowledge search service (#35)`
- `fix:` bug fix — `fix: delete temp files in finally block`
- `chore:` deps/config/tooling — `chore: add cognee dependencies to requirements`
- `docs:` research/docs — `docs: cognee pipeline notes`
- `test:` tests only — `test: add test_cognee smoke test`

**PR body:** must include `Closes #<number>` — Claude's ticket compliance check depends on this.

## Code review checklist
- `run_pipeline()` sanitizes client names via `sanitize_dataset_name()` from `utils/validation.py`
- `cognify()` never called without a prior `cognee.add()`
- Cognee operations in `run_pipeline()` use `asyncio.wait_for()` with `COGNEE_TIMEOUT_SECONDS` (default 300s)
- Temp files (`/tmp/cognee_uploads/`) deleted in `finally` block of `run_pipeline()`
- All Cognee operations use `async/await` — no blocking I/O in async routes
- Exceptions caught and returned as `HTTPException` — no raw tracebacks to client
- Search endpoint defaults to `SearchType.GRAPH_COMPLETION`
- Allowed upload extensions: `.pdf`, `.csv`, `.txt` — max 5 files per request
- Stale documents (stuck in `processing` >30 min) are auto-recovered to `failed` on startup
