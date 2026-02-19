-- -----------------------------------------------------------------------------
-- MIGRATION 016: CSV SUPPORT & 1:N EXTRACTED FILES
-- -----------------------------------------------------------------------------
-- Purpose: 
-- Allow multiple extracted entries (rows) for a single uploaded file.
-- Changes the primary key of extracted_files from file_id to a new id.
-- Adds row_index column.
-- -----------------------------------------------------------------------------

-- 1. Modify extracted_files table structure
-- We need to drop the existing primary key constraint. 
-- The constraint name is usually "extracted_files_pkey" but let's be safe.

ALTER TABLE extracted_files DROP CONSTRAINT IF EXISTS extracted_files_pkey;

-- Add new ID column
ALTER TABLE extracted_files 
    ADD COLUMN IF NOT EXISTS id UUID DEFAULT gen_random_uuid() PRIMARY KEY;

-- Keep file_id as Foreign Key, but allow duplicates (1:N)
-- It already references raw_files(file_id) ON DELETE CASCADE via table definition.
-- We just removed the PK constraint, so it's now just a column with an FK constraint.

-- Add row_index to track CSV rows
ALTER TABLE extracted_files
    ADD COLUMN IF NOT EXISTS row_index INT;

-- 2. Indexes
-- Ensure file_id is indexed for performance (it was part of PK before, so index might be gone if it was implicitly creating one)
CREATE INDEX IF NOT EXISTS idx_extracted_files_file_id ON extracted_files(file_id);

-- 3. Cleanup existing data (Optional)
-- Existing entries will have a generated UUID for 'id' and NULL for 'row_index'.
-- We can set row_index = 0 for them.
UPDATE extracted_files SET row_index = 0 WHERE row_index IS NULL;
