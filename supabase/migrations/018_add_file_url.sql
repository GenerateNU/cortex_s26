-- Add file_url column for raw file storage reference (Cloudflare R2 key)
ALTER TABLE cortex_documents ADD COLUMN IF NOT EXISTS file_url TEXT;

-- Nullify any legacy document_type values that won't satisfy the new constraint
UPDATE cortex_documents
SET document_type = NULL
WHERE document_type IS NOT NULL
  AND document_type NOT IN ('RFQ', 'PO', 'CFG', 'Client CSV', 'Sales CSV');

-- Replace old document_type constraint with updated type list
ALTER TABLE cortex_documents DROP CONSTRAINT IF EXISTS cortex_documents_document_type_check;
ALTER TABLE cortex_documents ADD CONSTRAINT cortex_documents_document_type_check
  CHECK (document_type IN ('RFQ', 'PO', 'CFG', 'Client CSV', 'Sales CSV'));
