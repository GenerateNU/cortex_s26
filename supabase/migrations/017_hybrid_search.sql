-- -----------------------------------------------------------------------------
-- MIGRATION 017: HYBRID SEARCH (Semantic + Keyword)
-- -----------------------------------------------------------------------------
-- Purpose: 
-- Add hybrid search function combining pgvector semantic search with 
-- Postgres full-text keyword search for better natural language query handling
-- -----------------------------------------------------------------------------

-- Hybrid search function combining vector similarity and keyword matching
CREATE OR REPLACE FUNCTION hybrid_search(
  query_text text,
  query_embedding vector(768),
  match_threshold float DEFAULT 0.3,
  match_count int DEFAULT 10
)
RETURNS TABLE (
  file_id uuid,
  file_name text,
  file_type file_type_enum,
  summary text,
  extracted_json jsonb,
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
    -- Combined score (70% semantic + 30% keyword) - can change later to better balance relevance
    ((1 - (ef.embedding <=> query_embedding)) * 0.7 + 
     ts_rank( --Built in TF-IDF Scoring--
       to_tsvector('english', COALESCE(ef.summary, '') || ' ' || COALESCE(ef.file_name, '')),
       plainto_tsquery('english', query_text) -- Automatically extracts keywords--
     ) * 0.3) as similarity
  FROM extracted_files ef
  WHERE 
    ef.embedding IS NOT NULL
    AND (
      -- Match either semantically OR by keyword
      (1 - (ef.embedding <=> query_embedding)) > match_threshold
      OR to_tsvector('english', COALESCE(ef.summary, '') || ' ' || COALESCE(ef.file_name, ''))
         @@ plainto_tsquery('english', query_text)
    )
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;

-- Add GIN indexes for keyword search performance
CREATE INDEX IF NOT EXISTS idx_summary_fulltext 
ON extracted_files USING GIN (to_tsvector('english', summary));

CREATE INDEX IF NOT EXISTS idx_filename_fulltext
ON extracted_files USING GIN (to_tsvector('english', file_name));

-- -----------------------------------------------------------------------------
-- END MIGRATION 017
-- -----------------------------------------------------------------------------