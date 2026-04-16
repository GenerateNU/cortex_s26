# Cortex

Document knowledge graph system powered by Cognee. Ingests PDFs/CSVs/text via `cognee.add()` → `cognee.cognify()`, then serves knowledge-graph search via `SearchType.GRAPH_COMPLETION`.

## What to ignore
- `archive/` — deprecated, do not review
- `frontend/` — deprecated, not in active development
- `backend/app/services/extraction/` — old ETL pipeline, being replaced
- `supabase/` — not part of current sprint

## Active codebase (review here)
- `backend/app/` — all active code
- `backend/tests/` — pytest tests

## Tech stack
- FastAPI + Uvicorn (Python 3.10+)
- Cognee (`cognee[postgres,gemini]>=0.5.5`) — knowledge graph engine
  - Graph store: Kuzu (embedded, `.cognee_system/`)
  - Vector store: pgvector via Supabase PostgreSQL
  - LLM: Google Gemini (`LLM_PROVIDER=gemini`)
  - Embeddings: configured via `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL`
- Supabase — document metadata, auth, async client
- LiteLLM — LLM abstraction layer
- Cloudflare R2 — raw file storage (pre-signed URLs via `boto3`)
- Ruff for linting/formatting

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
- `app/main.py` — FastAPI app, lifespan (Supabase → webhooks → queue → Cognee)
- `app/api.py` — central router, mounts all sub-routers under `/api`
- `app/cognee_config.py` — `setup_cognee()`, wired into lifespan
- `app/routes/documents.py` — upload, search, graph, list, get, file-url
- `app/services/ingest.py` — `ingest_document()`, `_extract_structured_data()`, `check_cognee_storage()` (legacy ingest path; also exports its own `search_knowledge_graph()`)
- `app/services/cognee_service.py` — `search_knowledge_graph()` (used by `/documents/search` route; separate from `ingest.py`'s version)
- `app/services/document_pipeline.py` — `run_pipeline()` (background ingest orchestration)
- `app/services/document_metadata_service.py` — Supabase CRUD for document records
- `app/services/graph_service.py` — `get_graph_data()` for D3 visualization
- `app/services/storage.py` — `get_presigned_url()` for Cloudflare R2
- `app/utils/validation.py` — `validate_dataset_name()`
- `app/core/` — Supabase client, LiteLLM client, webhooks, dependencies

### Other route modules
- `app/routes/search_routes.py` — legacy semantic/RAG search (Supabase embeddings)
- `app/routes/classification_routes.py` — document classification
- `app/routes/migration_routes.py` — data migration utilities
- `app/routes/pattern_recognition_routes.py` — pattern recognition
- `app/routes/preprocess_routes.py` — preprocessing pipeline

## Running the project
```bash
cd backend
python -m uvicorn app.main:app --reload
```

## Running tests
```bash
cd backend && pytest
```

## Linting (enforced in CI on every PR)
```bash
cd backend && ruff check   # must pass before merge
cd backend && ruff format  # auto-format
```

## Required environment variables

See `.env.example` for a copy-paste template.

```
# Supabase (required — used by lifespan, document metadata, search)
SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

# LLM / Embeddings
LLM_PROVIDER, LLM_MODEL, LLM_API_KEY
EMBEDDING_PROVIDER, EMBEDDING_MODEL, EMBEDDING_API_KEY

# Cognee persistence (read by Cognee SDK internally, not by app code)
VECTOR_DB_PROVIDER, VECTOR_DB_URL
DB_PROVIDER, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# Webhooks (optional — file extraction disabled without these)
WEBHOOK_BASE_URL, WEBHOOK_SECRET

# Object storage (optional — Cloudflare R2)
# ⚠ Known mismatch: storage.py reads R2_ACCESS_KEY_ID / R2_SECRET_KEY
#   but .env.example defines CLOUDFLARE_R2_ACCESS_KEY_ID / CLOUDFLARE_R2_SECRET_KEY.
#   Use the names that storage.py reads:
R2_ACCESS_KEY_ID, R2_SECRET_KEY, CLOUDFLARE_R2_ENDPOINT, CLOUDFLARE_R2_BUCKET_NAME
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
- `run_pipeline()` sanitizes client names via regex (`[^A-Za-z0-9_]` → `_`); `validate_dataset_name()` in `utils/validation.py` exists but is not currently wired into the pipeline
- `cognify()` never called without a prior `cognee.add()`
- Temp files (`/tmp/cognee_uploads/`) deleted in `finally` block of `run_pipeline()`
- All Cognee operations use `async/await` — no blocking I/O in async routes
- Exceptions caught and returned as `HTTPException` — no raw tracebacks to client
- Search endpoint defaults to `SearchType.GRAPH_COMPLETION`
- `ingest.py` error types (`kuzu_storage`, `llm_api`, `vector_dimension_mismatch`, `no_data_added`) must be mapped to appropriate HTTP status codes in route layer
- Allowed upload extensions: `.pdf`, `.csv`, `.txt` — max 5 files per request
