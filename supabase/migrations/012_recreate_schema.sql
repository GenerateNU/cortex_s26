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
