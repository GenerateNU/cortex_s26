-- -----------------------------------------------------------------------------
-- KNOWLEDGE BASE SCHEMA RE-CREATION SCRIPT
-- -----------------------------------------------------------------------------
-- Purpose:
-- This script completely resets the schema for file storage, extraction, and
-- relationship management. It drops existing tables and types to ensure a
-- clean slate and recreates them according to the specified design.
--
-- Tables created:
-- 1. raw_files
-- 2. extracted_files
-- 3. relationships
-- 4. file_relationships
--
-- Enums created:
-- 1. file_type_enum
-- -----------------------------------------------------------------------------

-- 1. CLEANUP
-- Drop tables in dependency order to avoid constraint errors
DROP TABLE IF EXISTS file_relationships CASCADE;
DROP TABLE IF EXISTS relationships CASCADE;
DROP TABLE IF EXISTS extracted_files CASCADE;
DROP TABLE IF EXISTS raw_files CASCADE;

-- Drop deprecated tables (including multi-tenancy and old logic)
DROP TABLE IF EXISTS file_uploads CASCADE;
DROP TABLE IF EXISTS classifications CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;
DROP TABLE IF EXISTS webhook_config CASCADE;
DROP TABLE IF EXISTS migrations CASCADE;

-- Note: DO NOT DROP auth.users or auth.identities as these are system tables needed for Supabase Auth.

-- Drop custom types
DROP TYPE IF EXISTS file_type_enum CASCADE;
DROP TYPE IF EXISTS relationship_type CASCADE; -- Old enum from previous schema

-- 2. EXTENSIONS
-- Required for UUID generation (gen_random_uuid())
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 3. ENUMS
-- Define allowed file types for extracted documents
CREATE TYPE file_type_enum AS ENUM (
    'RFQ',
    'PO',
    'ProdSpec',
    'Sales',
    'Customers'
);

-- 4. TABLES

-- -----------------------------------------------------------------------------
-- Table: raw_files
-- Purpose: Stores metadata for uploaded files only.
--          Acts as the source of truth for file existence.
-- -----------------------------------------------------------------------------
CREATE TABLE raw_files (
    file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_name TEXT NOT NULL,
    file_link TEXT NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- Table: extracted_files
-- Purpose: Stores structured data extracted from raw_files.
-- Relationship: Strict 1:1 with raw_files.
--               Enforced by making file_id both PK and FK.
-- Constraint: Deleting a raw_file automatically deletes its extracted data.
-- -----------------------------------------------------------------------------
CREATE TABLE extracted_files (
    file_id UUID PRIMARY KEY REFERENCES raw_files(file_id) ON DELETE CASCADE,
    file_type file_type_enum,
    summary TEXT,
    jsonb_data JSONB NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- Table: relationships
-- Purpose: Defines distinct business relationship types (e.g., "Supplier", "Competitor").
--          Currently stores name and description.
-- -----------------------------------------------------------------------------
CREATE TABLE relationships (
    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    relationship_name TEXT NOT NULL UNIQUE,
    relationship_description TEXT NOT NULL
);

-- -----------------------------------------------------------------------------
-- Table: file_relationships
-- Purpose: Junction table connecting files to relationships.
-- Relationship: Many-to-Many between raw_files and relationships.
-- Constraint: Deleting a file or relationship removes the connection.
-- -----------------------------------------------------------------------------
CREATE TABLE file_relationships (
    file_id UUID NOT NULL REFERENCES raw_files(file_id) ON DELETE CASCADE,
    relationship_id UUID NOT NULL REFERENCES relationships(relationship_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    confidence_score NUMERIC(4,3),
    source TEXT,
    -- Composite Primary Key ensures unique pairs (no duplicate relationships for same file)
    PRIMARY KEY (file_id, relationship_id)
);

-- 5. INDEXES

-- GIN index for fast JSONB querying on extracted data properties
CREATE INDEX idx_extracted_files_jsonb ON extracted_files USING gin (jsonb_data);

-- B-tree index for efficient filtering by file type
CREATE INDEX idx_extracted_files_type ON extracted_files (file_type);

-- B-tree index for reverse lookups on relationships (finding all files for a relationship)
-- (Forward lookup file_id -> relationships is covered by the PK)
CREATE INDEX idx_file_relationships_rel_id ON file_relationships (relationship_id);

-- -----------------------------------------------------------------------------
-- END OF SCRIPT
-- -----------------------------------------------------------------------------
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
-- MIGRATION 014: FIX RLS POLICIES FOR FRONTEND ACCESS

-- 1. Enable RLS on tables (good practice, though we will open them up for now)
ALTER TABLE raw_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE extracted_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE file_relationships ENABLE ROW LEVEL SECURITY;

-- 2. Create "Allow All" policies for valid MVP usage (Frontend uses anon key)
-- In a real prod app, you'd restrict this to authenticated users.

-- raw_files
CREATE POLICY "Allow public insert" ON raw_files FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public select" ON raw_files FOR SELECT USING (true);
CREATE POLICY "Allow public update" ON raw_files FOR UPDATE USING (true);
CREATE POLICY "Allow public delete" ON raw_files FOR DELETE USING (true);

-- extracted_files
CREATE POLICY "Allow public select extracted" ON extracted_files FOR SELECT USING (true);
CREATE POLICY "Allow public insert extracted" ON extracted_files FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update extracted" ON extracted_files FOR UPDATE USING (true);

-- relationships
CREATE POLICY "Allow public select relationships" ON relationships FOR SELECT USING (true);
CREATE POLICY "Allow public insert relationships" ON relationships FOR INSERT WITH CHECK (true);

-- file_relationships
CREATE POLICY "Allow public select file_rel" ON file_relationships FOR SELECT USING (true);
CREATE POLICY "Allow public insert file_rel" ON file_relationships FOR INSERT WITH CHECK (true);


-- 3. STORAGE POLICIES (Crucial for file upload)
-- Make sure the 'documents' bucket exists
INSERT INTO storage.buckets (id, name, public) 
VALUES ('documents', 'documents', true)
ON CONFLICT (id) DO NOTHING;

-- Allow public access to storage.objects for the 'documents' bucket
CREATE POLICY "Allow public upload" ON storage.objects
FOR INSERT WITH CHECK (bucket_id = 'documents');

CREATE POLICY "Allow public select" ON storage.objects
FOR SELECT USING (bucket_id = 'documents');

CREATE POLICY "Allow public update" ON storage.objects
FOR UPDATE USING (bucket_id = 'documents');
