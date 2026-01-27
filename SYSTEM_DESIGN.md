# Cortex ETL - Complete System Design Documentation

## Overview

Cortex ETL is an automated knowledge base creation system for manufacturing CPQ (Configure, Price, Quote) systems. It processes multi-format data (primarily PDFs) into structured, queryable databases with complete tenant isolation.

## Architecture Summary

### Technology Stack

- **Frontend**: React + TypeScript + Vite
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL via Supabase
- **AI Services**: LiteLLM + Google Gemini API
- **Deployment**: Docker Compose
- **Development**: Local Supabase stack

---

## System Components

### 1. Frontend Application (React + TypeScript)

**Location**: `frontend/src/`

#### Pages
- **LoginPage**: Authentication interface
- **AdminPage**: Admin dashboard for system management
- **DocumentPage**: Document viewing and management
- **ClusterVisualizationPage**: Visual representation of classification clusters

#### Key Hooks
- `classification.hooks.tsx` - Manage classification categories
- `files.hooks.tsx` - File upload and management
- `migrations.hooks.tsx` - Database migration tracking
- `patternRecognition.hooks.tsx` - Pattern recognition operations
- `preprocess.hooks.tsx` - Preprocessing job management
- `useRealtimeSubscription.tsx` - Real-time updates from Supabase

#### Contexts
- **AuthContext**: Session management and authentication
- **QueryContext**: React Query configuration for data fetching

---

### 2. Backend API (FastAPI)

**Location**: `backend/app/`

#### API Routes (`routes/`)

1. **Classification Routes** (`/api/classification`)
   - GET classifications for tenant
   - POST create/update classifications
   - POST classify individual files

2. **Preprocess Routes** (`/api/preprocess`)
   - POST retry extraction for failed files
   - Enqueues PDF processing jobs

3. **Webhook Routes** (`/api/webhooks`)
   - POST extract_data - Triggered by Supabase on file upload
   - Validates webhook secret for security

4. **Pattern Recognition Routes** (`/api/pattern-recognition`)
   - POST analyze relationships between classifications
   - Returns discovered patterns and relationships

5. **Migration Routes** (`/api/migrations`)
   - GET migrations for tenant
   - POST create new migration
   - POST execute pending migrations

#### Services Layer (`services/`)

**Preprocess Service**
- Manages PDF extraction pipeline
- Downloads files from Supabase Storage
- Orchestrates LiteLLM + Gemini for data extraction
- Generates vector embeddings for semantic search
- Tracks extraction status (queued → processing → complete/failed)

**Classification Service**
- CRUD operations for classification categories
- Assigns files to classifications
- Manages classification lifecycle
- Handles file unlinking when classifications are deleted

**Pattern Recognition Service**
- Analyzes relationships between classification categories
- Uses AI to detect patterns in document types
- Calculates relationship cardinality (one-to-one, one-to-many, many-to-many)
- Stores relationships with confidence scores

**Schema Generation Service**
- Pure function-based schema generation
- Converts classifications to SQL table names
- Generates CREATE TABLE migrations
- Creates foreign key constraints from relationships
- Handles PostgreSQL naming constraints (63 char limit)
- Deterministic and idempotent

**Migration Service**
- Stores migration SQL in database
- Executes migrations in sequence order
- Creates tenant-specific schemas
- Maintains migration history

#### Repositories Layer (`repositories/`)

Data access layer that abstracts Supabase operations:
- `ExtractionRepository` - extracted_files table operations
- `ClassificationRepository` - classifications table operations
- `RelationshipRepository` - relationships table operations
- `MigrationRepository` - migrations table operations
- `SchemaRepository` - Raw SQL execution for DDL

---

### 3. Processing Pipeline

#### Preprocessing Queue (`services/extraction/preprocessing_queue.py`)
- Async job queue for PDF processing
- Prevents blocking on large file uploads
- Status tracking and monitoring
- Worker-based processing model

#### PDF Extraction Strategy (`services/extraction/pdf_strategy.py`)
- Uses LiteLLM to orchestrate AI providers
- Sends PDFs to Google Gemini for structured extraction
- Returns JSON-formatted data
- Handles extraction errors and retries

#### Embeddings Generation (`services/extraction/embeddings.py`)
- Generates vector embeddings for document content
- Enables semantic search capabilities
- Stores embeddings in PostgreSQL vector column

#### Pattern Recognition Algorithm (`services/pattern_recognition/`)
- AI-powered relationship detection
- Analyzes document content and classifications
- Determines relationship types and cardinality
- Calculates confidence scores

---

### 4. Database Architecture

#### Main Public Schema (Shared Infrastructure)

**tenants**
- Stores tenant organizations
- Each tenant gets isolated schema

**file_uploads**
- Tracks uploaded PDF files
- Links to tenant and classification
- References file in Supabase Storage

**extracted_files**
- Stores extracted structured data (JSONB)
- Contains vector embeddings
- Tracks extraction status and errors
- One-to-one with file_uploads

**classifications**
- User-defined document categories
- Tenant-scoped
- Examples: "Robot Specifications", "Product Brochure", "Safety Manual"

**relationships**
- AI-discovered relationships between classifications
- Includes cardinality and confidence score
- Used to generate foreign keys in tenant schemas

**migrations**
- SQL migration history per tenant
- Sequence-ordered execution
- Enables schema versioning

#### Tenant-Specific Schemas (Isolated Data)

Each tenant gets a dedicated PostgreSQL schema (e.g., `tenant_kawasaki_robotics`)

**Dynamic Table Creation**
- Each classification becomes a table
- Table name derived from classification name
- Example: "Robot Specifications" → `robot_specifications`

**Foreign Key Relationships**
- Relationships table defines foreign keys
- Example: `robot_specifications.product_brochure_id` → `product_brochure.id`

**Data Storage**
- Extracted JSONB data stored in tables
- Queryable via SQL
- Tenant-isolated by schema

#### Storage Buckets

**tenant-files**
- Stores original PDF files
- Organized by tenant_id/filename
- Row-Level Security (RLS) enforces tenant isolation

---

## Complete Data Flow Workflow

### Phase 1: File Upload & Extraction

1. **User uploads PDF** via Frontend
2. **File stored** in Supabase Storage bucket (`tenant-files`)
3. **Record created** in `file_uploads` table
4. **Database webhook triggers** on new `file_upload` insert
5. **Webhook calls** Backend `/api/webhooks/extract_data` endpoint

### Phase 2: Preprocessing Pipeline

6. **Preprocessing Queue** receives job, creates `extracted_files` entry with status "queued"
7. **Worker picks up job**, updates status to "processing"
8. **PDF downloaded** from Supabase Storage
9. **LiteLLM + Gemini** extracts structured data from PDF
10. **Embedding vector** generated for document content
11. **Results stored** in `extracted_files` table with status "complete"

### Phase 3: Classification

12. **Admin/User creates** classification categories (e.g., "Robot Specs", "Product Brochure")
13. **Classifications stored** in `classifications` table
14. **User manually assigns** files to classifications
15. **file_uploads.classification_id** updated

### Phase 4: Pattern Recognition

16. **User triggers** pattern recognition analysis
17. **System fetches** all classifications and extracted files with embeddings
18. **AI analyzes** relationships between classification categories
19. **Relationships stored** in `relationships` table
    - Example: "Robot Specs" → "Product Brochure" (one-to-many)

### Phase 5: Schema Generation & Migration

20. **User requests** schema generation
21. **System reads** classifications and relationships
22. **Generates SQL migrations** to create tenant-specific tables
23. **Each classification** becomes a table (e.g., `robot_specifications`)
24. **Relationships** become foreign keys
25. **Migrations stored** in `migrations` table
26. **Migrations executed** to create actual database schema
27. **Tenant can now query** their custom schema via SQL

### Real-time Updates

- **Supabase Realtime** subscriptions push updates to Frontend
- Status changes, new files, completed extractions update UI instantly
- No polling required

---

## Key Design Patterns

### 1. Multi-Tenant Isolation

**Schema-per-Tenant**
- Each tenant gets a dedicated PostgreSQL schema
- Complete data isolation
- No cross-tenant queries possible
- Scales to thousands of tenants

**Row-Level Security (RLS)**
- Supabase RLS policies on shared tables
- Enforces tenant_id filtering
- Storage bucket access control

### 2. Async Processing

**Job Queue Pattern**
- PDF extraction is async and non-blocking
- Status tracking (queued → processing → complete/failed)
- Enables retry logic
- Prevents timeout on large files

### 3. Event-Driven Architecture

**Database Webhooks**
- Supabase triggers webhook on file upload
- Decouples upload from processing
- Enables horizontal scaling

**Realtime Subscriptions**
- Frontend subscribes to database changes
- Instant UI updates
- No polling overhead

### 4. Repository Pattern

**Data Access Abstraction**
- Repositories encapsulate Supabase operations
- Services depend on repositories, not raw client
- Testable and mockable
- Clean separation of concerns

### 5. Pure Functions for Schema Generation

**Deterministic Schema Generation**
- `SchemaGenerationService.create_migrations()` is a pure function
- Input: classifications + relationships + existing migrations
- Output: new migration SQL
- No side effects, fully testable
- Idempotent - same input always produces same output

---

## Security Considerations

### Authentication
- Supabase Auth for user management
- JWT-based session tokens
- Role-based access control (Admin vs Tenant)

### Tenant Isolation
- Schema-per-tenant prevents data leakage
- RLS policies on shared tables
- Storage bucket policies

### Webhook Security
- Webhook secret validation
- HMAC signature verification
- Prevents unauthorized extraction requests

### API Security
- CORS middleware configured
- Dependency injection for auth checks
- Service role key for backend operations

---

## Development Workflow

### Local Setup

```bash
npm run fresh
```

This command:
1. Generates environment variables
2. Starts local Supabase stack
3. Builds and runs frontend/backend containers

### Access Points
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Supabase Studio: http://localhost:54323

### Development Credentials
- Admin: admin@cortex.com / password
- Tenants: eng@kawasaki-robotics.com / password (etc.)

---

## Deployment Architecture

### Docker Compose

**Services**
- `backend` - FastAPI container (port 8000)
- `frontend` - Vite dev server (port 5173)
- Supabase stack (via `supabase start`)

**Networking**
- Custom network: `cortex-network`
- Backend can access Supabase via `host.docker.internal`

**Environment Variables**
- Generated by `init-dev.js`
- Stored in `.env` (gitignored)
- Includes Supabase keys, webhook secrets, API keys

### Production Considerations

**Cloud Deployment**
- Frontend: Static hosting (Vercel, Netlify)
- Backend: Container hosting (Cloud Run, ECS)
- Database: Supabase Cloud (managed PostgreSQL)

**Scaling**
- Preprocessing queue can be distributed (Redis/Celery)
- Multiple backend workers for parallel processing
- Database connection pooling

---

## Future Enhancements

### Planned Features
1. **CSV/Excel Support** - Extend beyond PDFs
2. **API Ingestion** - Pull data from external APIs
3. **Advanced Querying** - Natural language to SQL
4. **Visualization** - Auto-generate charts from data
5. **Export** - Export tenant schemas to other formats

### Technical Improvements
1. **Caching** - Redis for frequently accessed data
2. **Background Jobs** - Celery for distributed processing
3. **Monitoring** - Prometheus/Grafana for observability
4. **Testing** - Comprehensive test coverage
5. **CI/CD** - Automated deployment pipeline

---

## Troubleshooting

### Common Issues

**Extraction Fails**
- Check GEMINI_API_KEY is valid
- Verify PDF is not corrupted
- Check backend logs for LiteLLM errors

**Webhook Not Triggering**
- Verify WEBHOOK_BASE_URL is accessible from Supabase
- Check WEBHOOK_SECRET matches database config
- Ensure `configure_webhooks()` ran on startup

**Schema Generation Errors**
- Ensure classifications exist
- Run pattern recognition before schema generation
- Check for PostgreSQL naming conflicts

**Tenant Isolation Issues**
- Verify RLS policies are enabled
- Check tenant_id is correctly set in session
- Ensure schema name matches tenant

---

## Conclusion

Cortex ETL provides a complete, production-ready solution for automated knowledge base creation. Its multi-tenant architecture, AI-powered extraction, and dynamic schema generation make it ideal for manufacturing CPQ systems and similar use cases requiring structured data from unstructured sources.

The system is designed for:
- **Scalability** - Schema-per-tenant isolation
- **Flexibility** - Dynamic schema generation
- **Reliability** - Async processing with status tracking
- **Security** - Complete tenant isolation
- **Extensibility** - Clean service architecture

For questions or contributions, see the main README.md.
