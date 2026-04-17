-- Add content_hash column for upload deduplication (SHA-256 hex digest).
ALTER TABLE cortex_documents ADD COLUMN IF NOT EXISTS content_hash TEXT;

CREATE INDEX IF NOT EXISTS idx_cortex_documents_content_hash
  ON cortex_documents(content_hash);
