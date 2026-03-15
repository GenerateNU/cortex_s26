-- -----------------------------------------------------------------------------
-- MIGRATION 018: ADD EXECUTE_SQL FUNCTION FOR LLM QUERIES
-- -----------------------------------------------------------------------------
-- Purpose:
-- Allow the backend to execute dynamically generated SQL queries
-- (e.g., queries produced by an LLM) through Supabase RPC.
--
-- The function returns results as JSON so they can be easily consumed
-- by the Supabase client.
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
    -- Wrap query so results are returned as JSON array
    EXECUTE format('SELECT json_agg(t) FROM (%s) t', query) INTO result;

    RETURN COALESCE(result, '[]'::json);
END;
$$;

-- 2. Grant execute permission to Supabase API roles
-- This allows the Supabase client to call the RPC
GRANT EXECUTE ON FUNCTION execute_sql(TEXT) TO anon, authenticated;

-- 3. Safety note
-- The backend must validate queries before calling this function.
-- Only SELECT queries should be allowed to avoid destructive operations.