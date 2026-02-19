-- -----------------------------------------------------------------------------
-- MIGRATION 013: BACKEND OVERHAUL & STRICT SCHEMA ENFORCEMENT
-- -----------------------------------------------------------------------------
-- Purpose: 
-- Align database with strict constraints from "Section 3" of the overhaul plan.
-- Adds vector support for Semantic Search.
-- -----------------------------------------------------------------------------

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. ENUMS
-- Ensure file_type_enum matches strict spec: RFQ, PO, ProdSpec, Sales, Customers
-- We drop and recreate to ensure no stale values from 012.
DROP TYPE IF EXISTS file_type_enum CASCADE;
CREATE TYPE file_type_enum AS ENUM (
    'RFQ',
    'PO',
    'ProdSpec',
    'Sales',
    'Customers'
);

-- Relationship Source Enum (Section 5)
DROP TYPE IF EXISTS relationship_source_enum CASCADE;
CREATE TYPE relationship_source_enum AS ENUM (
    'manual',
    'ai_inference',
    'filename-rule'
);

-- 3. TABLES UPDATES

-- raw_files: Ensure columns exist
-- (file_id, file_name, uploaded_at, file_link) - already created in 012.
-- No changes needed unless 012 wasn't run, but we assume it was.

-- extracted_files: Align with Section 3
-- - file_id (FK -> raw_files)
-- - file_name (New)
-- - file_type (Updated Enum - Re-added due to CASCADE drop)
-- - summary (New/Existing)
-- - extracted_json (Renamed from jsonb_data)
-- - embedding (New - Vector)

ALTER TABLE extracted_files 
    ADD COLUMN IF NOT EXISTS file_name TEXT,
    ADD COLUMN IF NOT EXISTS embedding vector(768),
    ADD COLUMN file_type file_type_enum; -- Re-add as it was dropped by CASCADE above

-- Rename jsonb_data to extracted_json if it exists
DO $$
BEGIN
  IF EXISTS(SELECT *
    FROM information_schema.columns
    WHERE table_name = 'extracted_files' AND column_name = 'jsonb_data')
  THEN
      ALTER TABLE extracted_files RENAME COLUMN jsonb_data TO extracted_json;
  END IF;
END $$;

-- relationships: Ensure exists
-- (relationship_id, relationship_name, relationship_description) - Matches 012.

-- file_relationships: Align with Section 3 + 5
-- - file_id
-- - relationship_id
-- - created_at
-- - confidence_score (float)
-- - source (New Enum)

ALTER TABLE file_relationships 
    ADD COLUMN IF NOT EXISTS source relationship_source_enum;

-- 4. INDEXES (Section 3 & 6)

-- Vector Index for Semantic Search (IVFFlat or HNSW)
CREATE INDEX IF NOT EXISTS idx_extracted_files_embedding 
ON extracted_files USING hnsw (embedding vector_cosine_ops);

-- Index for extracted_json (GIN)
CREATE INDEX IF NOT EXISTS idx_extracted_files_json 
ON extracted_files USING gin (extracted_json);

-- 5. FUNCTIONS (Section 6 - Search)

-- Function to match extracted_files by vector similarity
CREATE OR REPLACE FUNCTION match_extracted_files (
  query_embedding vector(768),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  file_id UUID,
  file_name TEXT,
  file_type file_type_enum,
  summary TEXT,
  extracted_json JSONB,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    ef.file_id,
    ef.file_name,
    ef.file_type,
    ef.summary,
    ef.extracted_json,
    1 - (ef.embedding <=> query_embedding) as similarity
  FROM extracted_files ef
  WHERE 1 - (ef.embedding <=> query_embedding) > match_threshold
  ORDER BY ef.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- -----------------------------------------------------------------------------
-- END MIGRATION 013
-- -----------------------------------------------------------------------------
