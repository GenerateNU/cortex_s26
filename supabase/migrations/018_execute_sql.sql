-- -----------------------------------------------------------------------------
-- MIGRATION 018: ADD EXECUTE_SQL FUNCTION FOR LLM QUERIES
-- -----------------------------------------------------------------------------
-- Purpose:
-- Allow the backend to execute LLm generated SQL queries.
-- -----------------------------------------------------------------------------

-- 1. Create execute_sql function
CREATE OR REPLACE FUNCTION execute_sql(query TEXT)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSON;
BEGIN
    RETURN QUERY EXECUTE format(
    'SELECT
        file_id,
        file_name,
        file_type,
        summary,
        extracted_json
     FROM (%s) q',
    query
  );

END;
$$;

-- 3. Safety note
-- The backend must validate queries before calling this function.
-- Only SELECT queries should be allowed.