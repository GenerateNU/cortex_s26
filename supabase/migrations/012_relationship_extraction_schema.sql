-- Relationship-ready extraction schema additions (backward compatible)

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type
    WHERE typname = 'document_file_type'
  ) THEN
    CREATE TYPE document_file_type AS ENUM (
      'RFQ',
      'PO',
      'Product Spec',
      'Sales',
      'Customers'
    );
  END IF;
END $$;

ALTER TABLE extracted_files
ADD COLUMN IF NOT EXISTS file_id UUID;

UPDATE extracted_files
SET file_id = id
WHERE file_id IS NULL;

ALTER TABLE extracted_files
ALTER COLUMN file_id SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'extracted_files_file_id_key'
  ) THEN
    ALTER TABLE extracted_files
    ADD CONSTRAINT extracted_files_file_id_key UNIQUE (file_id);
  END IF;
END $$;

ALTER TABLE extracted_files
ADD COLUMN IF NOT EXISTS filename TEXT;

UPDATE extracted_files ef
SET filename = fu.name
FROM file_uploads fu
WHERE fu.id = ef.source_file_id
  AND ef.filename IS NULL;

ALTER TABLE extracted_files
ADD COLUMN IF NOT EXISTS file_type document_file_type;

UPDATE extracted_files
SET file_type = 'Product Spec'
WHERE file_type IS NULL;

ALTER TABLE extracted_files
ALTER COLUMN file_type SET NOT NULL;

ALTER TABLE extracted_files
ADD COLUMN IF NOT EXISTS extracted_json JSONB;

UPDATE extracted_files
SET extracted_json = extracted_data
WHERE extracted_json IS NULL;

ALTER TABLE extracted_files
ADD COLUMN IF NOT EXISTS llm_summary TEXT;

CREATE INDEX IF NOT EXISTS idx_extracted_files_file_type
ON extracted_files(file_type);
